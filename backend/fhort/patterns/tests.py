"""Tests del motor de patrons.

Convenció del repo: `tests.py` pla dins de l'app, executat amb
`python manage.py test fhort.patterns` (el projecte NO fa servir pytest).

Els tests de l'engine són `unittest.TestCase` **purs** —sense `TenantTestCase` i sense
BD— perquè el motor no en necessita: és un paquet Python pur. Aquesta absència no és
un descuit, és la prova que la frontera hexagonal aguanta.

El material real (AMELIA, PolyPattern) és a `tests/fixtures/`. Els recomptes que
s'hi asserten són els que la diagnosi S0-B3 va censar a mà sobre el fitxer cru: si el
parser i el cens no coincideixen, un dels dos menteix.

⚠️ `patterns/tests/` (directori de fixtures) NO ha de tenir mai `__init__.py`, o
passaria a ser un paquet i desplaçaria aquest mòdul en la resolució d'imports.
"""
from __future__ import annotations

import hashlib
import io
import logging
import math
import unittest
from dataclasses import replace
from pathlib import Path

import ezdxf

# ezdxf avisa que R12 no exporta $INSUNITS cada cop que escrivim un fixture sintètic.
# És cert i és irrellevant (els fitxers reals tampoc no en porten): que no tapi els verds.
logging.getLogger('ezdxf').setLevel(logging.ERROR)

from fhort.patterns.engine.aama_reader import AAMAReader, fold_piece, unfold_piece
from fhort.patterns.engine.aama_writer import AAMAWriter, UnknownProfileError
from fhort.patterns.engine.errors import PatternParseError
from fhort.patterns.engine.ftt_pom_layer import (
    FTT_POM_LAYER,
    FTTPOMLayerReader,
    format_meta_text,
    format_pom_text,
    parse_pom_text,
)
from fhort.patterns.engine.geometry import (
    BoundaryData,
    Confidence,
    GradeRuleData,
    LayerRole,
    NotchData,
    PatternDocument,
    PieceData,
    POMAnchorData,
    PointData,
    PointKind,
    UnitsMethod,
)
from fhort.patterns.engine.grading_projection import (
    GradingContextError,
    GradingNotApproved,
    preview_per_talla,
    project,
)
from fhort.patterns.engine.operations import POMSpec, PointRef, move_points
from fhort.patterns.engine.measure import MeasureError, resoldre
from fhort.patterns.engine.roundtrip import compare, compare_grade_tables
from fhort.patterns.engine.dart_detection import (
    LLINDAR_PINCA,
    clau_pinca,
    detectar,
)
from fhort.patterns.preferences import (
    classifica_accio, preferencia_del_tram, rangs_apresos, registra, rol_de_peca)
from fhort.patterns.engine.seam_matching import (
    Candidat,
    LLINDAR_PROPOSTA,
    PES_LONGITUD,
    PES_NOMS,
    PES_PIQUETS,
    PES_PREFERENCIA,
    PES_PREFERENCIA_CONTRA,
    TOL_PIQUET_S,
    avaluar,
    casen_piquets,
    clau_parella,
    piquets_de_la_vora,
    piquets_del_tram,
    projectar,
    proposar,
    senyal_longitud,
    senyal_noms,
    senyal_preferencia,
)
from fhort.patterns.engine.segments import (
    acumulats_vora, SegmentError, fraccio_tram, longitud_tram,
                                            longitud_vora, segmentar_peca, segmentar_vora,
                                            tram_entre_punts)
from fhort.patterns.engine.natural_segments import (
    LLINDAR_CANTONADA_GRAUS, cantonades_naturals, desviacio_angular,
    segmentar_peca_natural, segmentar_vora_natural, vertexs_de_piquet)
from fhort.patterns.engine.sew import (MENA_EXCES, MENA_SOLAPAMENT, CostatPinca, Descompte,
                                       TramCosit, conte, descomptar_pinces, validar,
                                       validar_cobertura)
from fhort.patterns.engine.rul_reader import RULReader, coherencia_dxf_rul
from fhort.patterns.tolerance import graduar
from fhort.patterns.engine.rul_writer import RULWriter

# ── el que només fa falta per als tests de S3 (adaptadors: SÍ que toquen Django) ──
import datetime
from decimal import Decimal
import time
from unittest import mock
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.services_fitxers import DOWNLOAD_SALT as MODEL_FITXER_SALT
from fhort.models_app.services_fitxers import DOWNLOAD_TTL
from fhort.patterns.adapters import (DjangoGeometryStore, DjangoGradingSource,
                                     pom_specs, sew_specs)
from fhort.patterns.annotation_views import (PatternPOMViewSet, PatternSegmentViewSet,
                                             SewProposalRejectionViewSet, SewRelationSerializer,
                                             SewRelationViewSet, SewToleranceAcceptanceViewSet,
                                             comprovar_costura)
from fhort.patterns.export import ExportBlocked, build_export
from fhort.patterns.models import (DartProposalRejection, ExportAcknowledgement, PatternFile,
                                   PatternPOM, PatternPoint, PatternSegment,
                                   SegmentPreference, SewProposalRejection, SewRelation,
                                   SewToleranceAcceptance)
from fhort.patterns.services import save_pattern_file
from fhort.patterns.serializers import PatternGeometrySerializer
from fhort.patterns.views import (PATTERN_DOWNLOAD_SALT, PATTERN_RUL_DOWNLOAD_SALT,
                                  PatternFileViewSet)
from fhort.pom.models import GarmentType, POMMaster
from fhort.tasks.models import GarmentTypeItem

FIXTURES = Path(__file__).parent / 'tests' / 'fixtures'
AMELIA_DXF = FIXTURES / 'AMELIA_AZUL_prova.dxf'
AMELIA_RUL = FIXTURES / 'AMELIA_AZUL_prova.rul'
#: El TATE (Brownie, model BRW-FW26-0001): el patró real amb què s'ha fet el QA del Taller.
#: Aporta el que l'AMELIA no té: **capa 14 (línia de cosit)**, que és la vora de la qual es
#: deriven els trams de veritat, i 10 peces amb vores tancades de 250+ punts.
TATE_DXF = FIXTURES / 'TATE_prova.dxf'

#: El material és el contracte. Si algú el toca, els recomptes de sota deixen de
#: voler dir res i val més que el test ho canti que no pas que passi en silenci.
AMELIA_DXF_MD5 = '2ae0006e003ebe17326187d79bb587d5'
TATE_DXF_MD5 = '419337df26602569253e243af735ab78'


def _dxf_bytes(doc) -> bytes:
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode('utf-8')


#: Mitja peça: el centre (x=0) recte —la vora que va sobre el doblec— i la resta del
#: contorn irregular, com una mitja esquena de debò. Un rectangle no serviria: tindria
#: dos eixos candidats i no distingiria un detector correcte d'un de sortós.
CONTORN_MITJA_PECA = [(0, 0), (100, 20), (120, 100), (90, 180), (0, 200), (0, 0)]


def _uploaded(path: Path) -> SimpleUploadedFile:
    return SimpleUploadedFile(path.name, path.read_bytes(),
                              content_type='application/octet-stream')


def mitja_peca_dxf() -> bytes:
    """AMELIA porta les peces senceres; el doblec s'ha de provar amb una peça a mitges."""
    doc = ezdxf.new('R12')
    block = doc.blocks.new(name='MITJA')
    block.add_polyline2d(CONTORN_MITJA_PECA, dxfattribs={'layer': '1'})
    for x, y in CONTORN_MITJA_PECA[:-1]:
        block.add_point((x, y), dxfattribs={'layer': '2'})
    block.add_point((60, 10), dxfattribs={'layer': '4'})  # un piquet al costat original
    doc.modelspace().add_blockref('MITJA', (0, 0))
    return _dxf_bytes(doc)


# ═════════════════════════════════════════════════════════════════════════════
# Material real — AMELIA (PolyPattern 11.0.1)
# ═════════════════════════════════════════════════════════════════════════════

class AmeliaFixtureTest(unittest.TestCase):
    def test_el_material_no_ha_canviat(self):
        md5 = hashlib.md5(AMELIA_DXF.read_bytes()).hexdigest()
        self.assertEqual(md5, AMELIA_DXF_MD5, 'El DXF de referència ha canviat.')


class AmeliaReaderTest(unittest.TestCase):
    """El parser contra el cens manual de la diagnosi S0-B3."""

    @classmethod
    def setUpClass(cls):
        cls.doc = AAMAReader().read(AMELIA_DXF.read_bytes())

    # ── peces ────────────────────────────────────────────────────────────────
    def test_quatre_peces_amb_els_seus_noms(self):
        self.assertEqual(
            self.doc.noms_peces, ('BACK', 'FRONT', 'BACK_LINI', 'FRONT_LINI')
        )

    def test_recompte_de_punts_per_peca(self):
        """Cens de S0-B3. El contorn de tall va SENSE el vèrtex repetit del tancament."""
        esperat = {
            # peça:        (tall, internes, turn, curve, punts_totals)
            'BACK':        (28, 4, 22, 42, 64),
            'FRONT':       (38, 6, 22, 86, 108),
            'BACK_LINI':   (24, 0, 10, 14, 24),
            'FRONT_LINI':  (44, 2, 12, 50, 62),
        }
        for nom, (tall, internes, turn, curve, totals) in esperat.items():
            with self.subTest(peca=nom):
                p = self.doc.piece(nom)
                self.assertEqual(len(p.boundary(LayerRole.CUT).points), tall)
                self.assertEqual(len(p.boundaries_of(LayerRole.INTERNAL)), internes)
                self.assertEqual(self._kind(p, PointKind.TURN), turn)
                self.assertEqual(self._kind(p, PointKind.CURVE), curve)
                self.assertEqual(p.punts_totals, totals)

    def test_cap_vertex_queda_sense_classificar(self):
        """Els POINT de les capes 2 i 3 cobreixen el 100% dels vèrtexs.

        És el que valida el mecanisme de classificació per coincidència: si fallés,
        apareixerien vèrtexs UNCLASSIFIED.
        """
        for p in self.doc.pieces:
            with self.subTest(peca=p.nom_block):
                self.assertEqual(self._kind(p, PointKind.UNCLASSIFIED), 0)

    def test_contorns_tancats_per_geometria(self):
        """Els CAD reals repeteixen el primer vèrtex en lloc d'activar el flag."""
        for p in self.doc.pieces:
            with self.subTest(peca=p.nom_block):
                self.assertTrue(p.boundary(LayerRole.CUT).closed)

    def test_piquets_i_grain(self):
        for p in self.doc.pieces:
            with self.subTest(peca=p.nom_block):
                self.assertEqual(len(p.notches), 2)
                self.assertIsNotNone(p.grain)

    def test_bounding_box_de_la_esquena(self):
        cut = self.doc.piece('BACK').boundary(LayerRole.CUT)
        xs = [pt.x for pt in cut.points]
        ys = [pt.y for pt in cut.points]
        self.assertAlmostEqual(max(xs) - min(xs), 524.7, places=1)
        self.assertAlmostEqual(max(ys) - min(ys), 695.0, places=1)

    # ── el que NO hi és ──────────────────────────────────────────────────────
    def test_sense_linia_de_cosit(self):
        """AMELIA no porta capa 14. No s'assumeix: es constata.

        És el fet que deixa S7 sense font per derivar el tall per offset del cosit.
        """
        self.assertFalse(self.doc.te_cosit)
        for p in self.doc.pieces:
            self.assertFalse(p.has_sew)
            self.assertIsNone(p.boundary(LayerRole.SEW))

    def test_sense_doblec(self):
        for p in self.doc.pieces:
            self.assertFalse(p.has_fold)

    # ── empremta ─────────────────────────────────────────────────────────────
    def test_la_font_es_polypattern(self):
        """Reatribució: el fitxer ho diu ell mateix (TEXT 'Author: PolyPattern')."""
        self.assertEqual(self.doc.fingerprint.font_cad, 'polypattern')
        self.assertEqual(self.doc.fingerprint.dxf_version, 'AC1009')  # R12

    def test_unitats_deduides_per_geometria_amb_confianca_alta(self):
        """La HEADER és buida: no hi ha $INSUNITS. El factor es dedueix i consta."""
        u = self.doc.fingerprint.unitats
        self.assertEqual(u.factor_to_mm, 1.0)
        self.assertIs(u.metode, UnitsMethod.GEOMETRY)
        self.assertIs(u.confianca, Confidence.HIGH)  # corroborat pel TEXT 'Units: Metric'
        self.assertIn('mm', u.evidencia)

    def test_capa_15_no_catalogada_es_preserva(self):
        """Una capa fora de l'estàndard no és un error: es registra i el fitxer es llegeix."""
        fp = self.doc.fingerprint
        self.assertEqual(fp.capes_desconegudes, ('15',))
        self.assertEqual(fp.capes_presents, ('1', '2', '3', '4', '7', '8', '15'))
        for p in self.doc.pieces:
            self.assertEqual(p.unknown_layers, ('15',))

    def test_les_capes_aama_no_estan_declarades_a_la_taula_layers(self):
        self.assertEqual(self.doc.fingerprint.capes_declarades, ('0', 'Defpoints'))

    def test_separador_decimal_per_camp(self):
        """Punt a les coordenades i coma als TEXT, dins el mateix fitxer."""
        self.assertEqual(
            self.doc.fingerprint.separador_decimal,
            {'coordenades': '.', 'text': ','},
        )

    # ── metadades de peça ────────────────────────────────────────────────────
    def test_metadades_de_peca_amb_coma_decimal(self):
        p = self.doc.piece('BACK')
        self.assertEqual(p.metadata.piece_name, 'BACK')
        self.assertEqual(p.metadata.size, 'M')
        self.assertEqual(p.metadata.quantity, 1.0)      # ve de 'Quantity: 1,0'
        self.assertEqual(p.metadata.material, 'SHL')
        self.assertEqual(self.doc.piece('BACK_LINI').metadata.material, 'LINING')

    def test_la_regla_de_grading_va_als_punts_de_gir_no_als_de_corba(self):
        """El TEXT '# 1' seu sobre el punt: és el lligam amb `RULE: DELTA 1` del RUL.

        I hi seu de manera SELECTIVA — el fitxer real ho diu clar: **tots** els punts
        de gir porten regla i **cap** punt de corba no en porta. És la llei que sosté
        l'operació atòmica de S7: els punts de gir es mouen per regla; els de corba no
        es graden, flueixen (reflow) entre els que sí.
        """
        regles = set()
        for p in self.doc.pieces:
            with self.subTest(peca=p.nom_block):
                for b in p.boundaries:
                    for pt in b.points:
                        if pt.kind is PointKind.TURN:
                            self.assertIsNotNone(pt.grade_rule)
                            regles.add(pt.grade_rule)
                        elif pt.kind is PointKind.CURVE:
                            self.assertIsNone(pt.grade_rule)
                for n in p.notches:
                    self.assertIsNotNone(n.grade_rule)
        self.assertEqual(regles, {1})

    def _kind(self, piece, kind) -> int:
        return sum(1 for b in piece.boundaries for pt in b.points if pt.kind is kind)


class AmeliaRULTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = RULReader().read(AMELIA_RUL.read_bytes())

    def test_estructura_de_la_taula(self):
        t = self.table
        self.assertEqual(t.talles, ('XS', 'S', 'M', 'L', 'XL'))
        self.assertEqual(t.talla_base, 'M')
        self.assertEqual(t.base_index, 2)
        self.assertEqual(t.unitats, 'METRIC')
        self.assertEqual(t.aama_version, 'ANSI/AAMA-292-B')
        self.assertIn('PolyPattern', t.autor)
        self.assertEqual(t.issues, ())

    def test_una_regla_amb_deltes_a_zero(self):
        """Els valors són zero; el que es testeja és que l'estructura hi és."""
        self.assertEqual(set(self.table.regles), {1})
        deltes = self.table.regles[1].deltes
        self.assertEqual(set(deltes), {'XS', 'S', 'M', 'L', 'XL'})
        self.assertEqual(deltes['XL'], (0.0, 0.0))
        self.assertEqual(self.table.regles[1].delta('XS'), (0.0, 0.0))

    def test_coherencia_amb_el_dxf_germa(self):
        """SAMPLE SIZE:M del RUL == Size: M de les 4 peces, i la regla 1 existeix."""
        doc = AAMAReader().read(AMELIA_DXF.read_bytes())
        self.assertEqual(coherencia_dxf_rul(doc, self.table), [])

    def test_denuncia_la_incoherencia_de_talla(self):
        """Un RUL d'un altre model no ha de colar."""
        altre = RULReader().read(
            AMELIA_RUL.read_bytes().replace(b'SAMPLE SIZE:M', b'SAMPLE SIZE:L')
        )
        doc = AAMAReader().read(AMELIA_DXF.read_bytes())
        codis = [i.codi for i in coherencia_dxf_rul(doc, altre)]
        self.assertIn('size_mismatch', codis)


# ═════════════════════════════════════════════════════════════════════════════
# Camins que el material real no exercita — fixtures sintètics
# ═════════════════════════════════════════════════════════════════════════════

class DoblecTest(unittest.TestCase):
    """AMELIA porta les peces senceres, així que el doblec es prova amb una peça
    dibuixada a mitges, que és com arriben les peces simètriques d'altres CAD."""

    def test_detecta_leix_de_doblec_per_geometria(self):
        doc = AAMAReader().read(mitja_peca_dxf())
        piece = doc.piece('MITJA')
        self.assertTrue(piece.has_fold)
        fold = piece.doblec_original
        self.assertAlmostEqual(fold.eix_x1, 0.0)
        self.assertAlmostEqual(fold.eix_x2, 0.0)
        self.assertFalse(fold.materialitzat)

    def test_desplegar_dobla_lample_i_es_reversible(self):
        doc = AAMAReader().read(mitja_peca_dxf())
        mitja = doc.piece('MITJA')
        sencera = unfold_piece(mitja)

        xs_mitja = [p.x for p in mitja.boundary(LayerRole.CUT).points]
        xs_sencera = [p.x for p in sencera.boundary(LayerRole.CUT).points]
        self.assertAlmostEqual(max(xs_mitja) - min(xs_mitja), 120.0)
        self.assertAlmostEqual(max(xs_sencera) - min(xs_sencera), 240.0)

        # L'eix es conserva per poder tornar a plegar la peça a S2.
        self.assertTrue(sencera.doblec_original.materialitzat)
        self.assertTrue(sencera.has_fold)
        # Els punts de l'eix són frontissa: no es dupliquen.
        a_leix = sum(1 for p in xs_sencera if abs(p) < 0.01)
        self.assertEqual(a_leix, 2)

    def test_desplegar_una_peca_sencera_no_la_toca(self):
        doc = AAMAReader().read(AMELIA_DXF.read_bytes())
        back = doc.piece('BACK')
        self.assertIs(unfold_piece(back), back)


class FTTPOMLayerTest(unittest.TestCase):
    """La capa que exportem: s'escriu segons l'especificació de `ftt_pom_layer` i es
    torna a llegir com una taula. És el que farà el DXF autocontingut a S7."""

    def _dxf_amb_capa_ftt(self) -> bytes:
        doc = ezdxf.new('R12')
        msp = doc.modelspace()
        msp.add_line((0, 0), (525, 0), dxfattribs={'layer': FTT_POM_LAYER})
        msp.add_text(
            format_pom_text('POM-001', 'CHEST WIDTH', 525.0),
            dxfattribs={'layer': FTT_POM_LAYER},
        ).set_placement((262.5, 0))
        msp.add_line((0, 100), (0, 800), dxfattribs={'layer': FTT_POM_LAYER})
        msp.add_text(
            format_pom_text('POM-014', 'BACK LENGTH', 700.0),
            dxfattribs={'layer': FTT_POM_LAYER},
        ).set_placement((0, 450))
        msp.add_text(
            format_meta_text(3, model='BRW-26-SS-0002', ts='2026-07-12T18:00:00Z'),
            dxfattribs={'layer': FTT_POM_LAYER},
        ).set_placement((0, -50))
        # Soroll d'una altra capa: no ha de contaminar la taula.
        msp.add_line((9, 9), (9, 99), dxfattribs={'layer': '1'})
        return _dxf_bytes(doc)

    def test_la_capa_es_rellegeix_com_a_taula(self):
        doc = ezdxf.read(io.StringIO(self._dxf_amb_capa_ftt().decode()))
        poms, meta = FTTPOMLayerReader().read(doc)

        self.assertEqual([p.pom_code for p in poms], ['POM-001', 'POM-014'])
        pom = poms[0]
        self.assertEqual(pom.valor_mesurat_mm, 525.0)
        self.assertEqual(pom.definicio_mesura['nom'], 'CHEST WIDTH')
        self.assertEqual(pom.punts_ancora, ((0.0, 0.0), (525.0, 0.0)))
        self.assertEqual(meta, {
            'v': '3', 'src': 'fhort',
            'model': 'BRW-26-SS-0002', 'ts': '2026-07-12T18:00:00Z',
        })

    def test_el_format_del_text_es_el_de_lespecificacio(self):
        self.assertEqual(
            format_pom_text('POM-001', 'CHEST WIDTH', 525.0),
            'FTT "POM-001" CHEST WIDTH = 525.000 mm',
        )

    def test_un_codi_amb_espais_sobreviu_al_viatge(self):
        """ESMENA S7. L'especificació original deia que els codis anaven «sense espais».

        El catàleg real diu que no: hi ha `HI RLX` i `LEG OP`. Sense cometes, el parser en
        llegia el primer tros i el POM tornava dient-se `HI` — la capa que havia d'evitar
        errors n'introduïa un. Ho va caçar la porta d'autovalidació de l'exportació.
        """
        text = format_pom_text('HI RLX', 'Hip width (relaxed)', 576.162)
        self.assertEqual(text, 'FTT "HI RLX" Hip width (relaxed) = 576.162 mm')

        pom = parse_pom_text(text)
        self.assertEqual(pom.pom_code, 'HI RLX')
        self.assertEqual(pom.definicio_mesura['nom'], 'Hip width (relaxed)')
        self.assertEqual(pom.valor_mesurat_mm, 576.162)

    def test_la_forma_antiga_sense_cometes_encara_es_llegeix(self):
        """Un format que trenca els seus propis lliurables antics no és un format."""
        pom = parse_pom_text('FTT POM-001 CHEST WIDTH = 525.0 mm')
        self.assertEqual(pom.pom_code, 'POM-001')
        self.assertEqual(pom.valor_mesurat_mm, 525.0)

    def test_el_valor_no_perd_precisio_en_el_viatge(self):
        """Amb un sol decimal, 668.354 mm tornava com a 668.4: la capa no es podia fer
        servir per validar res, que és justament per a què serveix."""
        pom = parse_pom_text(format_pom_text('M-M79', 'TOTAL LENGTH', 668.354))
        self.assertAlmostEqual(pom.valor_mesurat_mm, 668.354, places=6)

    def test_un_dxf_de_client_no_te_capa_ftt_i_no_es_cap_error(self):
        doc = ezdxf.readfile(str(AMELIA_DXF))
        poms, meta = FTTPOMLayerReader().read(doc)
        self.assertEqual(poms, ())
        self.assertEqual(meta, {})


class DegradacioElegantTest(unittest.TestCase):
    """Un fitxer real, per rar que sigui, no fa petar el parser: dona un error amb
    detall. A S3 això serà un 422, mai un 500."""

    def test_fitxer_buit(self):
        with self.assertRaises(PatternParseError) as ctx:
            AAMAReader().read(b'')
        self.assertEqual(ctx.exception.issues[0].codi, 'empty_file')

    def test_escombraries(self):
        with self.assertRaises(PatternParseError) as ctx:
            AAMAReader().read(b'aixo no es un dxf' * 50)
        self.assertEqual(ctx.exception.issues[0].codi, 'corrupt_dxf')

    def test_el_detall_de_lerror_no_aboca_el_fitxer_sencer(self):
        with self.assertRaises(PatternParseError) as ctx:
            AAMAReader().read(b'aixo no es un dxf' * 500)
        self.assertLessEqual(len(ctx.exception.issues[0].missatge), 210)

    def test_dxf_valid_sense_peces(self):
        with self.assertRaises(PatternParseError) as ctx:
            AAMAReader().read(_dxf_bytes(ezdxf.new('R12')))
        self.assertEqual(ctx.exception.issues[0].codi, 'no_blocks')

    def test_lerror_es_serialitzable(self):
        try:
            AAMAReader().read(b'')
        except PatternParseError as exc:
            payload = exc.as_dict()
        self.assertIn('error', payload)
        self.assertEqual(payload['issues'][0]['codi'], 'empty_file')

    def test_rul_buit(self):
        with self.assertRaises(PatternParseError):
            RULReader().read(b'')

    def test_rul_sense_talles(self):
        with self.assertRaises(PatternParseError) as ctx:
            RULReader().read(b'version ANSI/AAMA-292-B\nRULE: DELTA 1 0.00, 0.00\nEND\n')
        self.assertEqual(ctx.exception.issues[0].codi, 'no_sizes')

    def test_rul_amb_deltes_que_no_quadren_es_llegeix_i_es_denuncia(self):
        """Degradació: no peta, però ho diu."""
        table = RULReader().read(
            b'UNITS: METRIC\nSAMPLE SIZE:M\nSIZE LIST:XS S M L XL\n'
            b'RULE: DELTA 1 1.00, 1.00 2.00, 2.00\nEND\n'
        )
        self.assertEqual([i.codi for i in table.issues], ['delta_count_mismatch'])
        self.assertEqual(table.regles[1].deltes['S'], (2.0, 2.0))
        self.assertEqual(table.regles[1].delta('XL'), (0.0, 0.0))  # forat → zero


# ═════════════════════════════════════════════════════════════════════════════
# S2 · ESCRIPTURA — el fitxer torna a sortir tal com va entrar
# ═════════════════════════════════════════════════════════════════════════════

class RoundtripAmeliaTest(unittest.TestCase):
    """`read(write(read(f))) ≡ read(f)`. La prova de foc del writer."""

    @classmethod
    def setUpClass(cls):
        cls.original = AAMAReader().read(AMELIA_DXF.read_bytes())
        cls.tornat = AAMAReader().read(AAMAWriter().write(cls.original))

    def test_round_trip_semanticament_identic(self):
        report = compare(self.original, self.tornat)
        self.assertTrue(report.ok, report.resum())
        self.assertEqual(report.desviacio_maxima_um, 0.0)
        self.assertEqual(report.punts_comparats, 266)

    def test_el_cens_dentitats_surt_clavat(self):
        """El writer reprodueix la llei dels TEXT de regla del CAD, no una versió
        raonable d'aquesta llei: per això el recompte quadra exactament."""
        self.assertEqual(
            self.tornat.fingerprint.cens_entitats,
            self.original.fingerprint.cens_entitats,
        )
        self.assertEqual(
            self.original.fingerprint.cens_entitats,
            {'TEXT': 123, 'POLYLINE': 16, 'POINT': 266, 'LINE': 4, 'INSERT': 4},
        )

    def test_les_seccions_buides_segueixen_buides(self):
        """ezdxf les ompliria. Un fitxer 'millorat' ja no és el fitxer del client."""
        self.assertTrue(self.tornat.fingerprint.header_buida)
        self.assertTrue(self.tornat.fingerprint.tables_buida)

    def test_la_coma_decimal_dels_TEXT_es_reprodueix(self):
        escrit = AAMAWriter().write(self.original).decode()
        self.assertIn('Quantity: 1,0', escrit)
        self.assertEqual(
            self.tornat.fingerprint.separador_decimal,
            {'coordenades': '.', 'text': ','},
        )

    def test_la_capa_desconeguda_15_sobreviu(self):
        """No entendre una capa no és excusa per perdre-la."""
        self.assertEqual(self.tornat.fingerprint.capes_desconegudes, ('15',))
        raw = self.tornat.piece('BACK').raw_entities
        self.assertEqual([(r.dxftype, r.layer, r.text) for r in raw],
                         [('TEXT', '15', 'BROWNEI RAM NARESH')])

    def test_perfil_desconegut_es_error_dur(self):
        """Mai un fallback silenciós: exportaria cap a un CAD real un fitxer amb
        l'empremta d'un altre."""
        with self.assertRaises(UnknownProfileError):
            AAMAWriter().write(self.original, perfil='tuka')

    def test_perfil_polypattern_explicit(self):
        doc = AAMAReader().read(AAMAWriter().write(self.original, perfil='polypattern'))
        self.assertTrue(compare(self.original, doc).ok)


class RoundtripRULTest(unittest.TestCase):
    def test_el_rul_surt_byte_a_byte_identic(self):
        orig = AMELIA_RUL.read_bytes()
        self.assertEqual(RULWriter().write(RULReader().read(orig)), orig)

    def test_round_trip_semantic_del_rul(self):
        ta = RULReader().read(AMELIA_RUL.read_bytes())
        tb = RULReader().read(RULWriter().write(ta))
        self.assertTrue(compare_grade_tables(ta, tb).ok)
        self.assertEqual(ta, tb)

    def test_amb_deltes_de_debo(self):
        """Els d'AMELIA són zero; el writer ha de saber escriure'n de reals, amb signe."""
        base = RULReader().read(AMELIA_RUL.read_bytes())
        deltes = {'XS': (-6.0, -2.5), 'S': (-3.0, -1.0), 'M': (0.0, 0.0),
                  'L': (3.0, 1.0), 'XL': (6.5, 2.5)}
        taula = replace(base, regles={1: GradeRuleData(1, deltes)})
        tornada = RULReader().read(RULWriter().write(taula))
        self.assertEqual(tornada.regles[1].deltes, deltes)


class FTTPOMLayerWriterTest(unittest.TestCase):
    """La capa que fa el DXF autocontingut: s'escriu, es rellegeix com a taula, i no
    embruta res del que ja hi havia."""

    def _amb_poms(self):
        doc = AAMAReader().read(AMELIA_DXF.read_bytes())
        back = doc.piece('BACK')
        pts = back.boundary(LayerRole.CUT).points
        poms = (
            POMAnchorData('POM-001', ((pts[0].x, pts[0].y), (pts[10].x, pts[10].y)),
                          {'nom': 'CHEST WIDTH'}, 525.0),
            POMAnchorData('POM-014', ((pts[3].x, pts[3].y), (pts[20].x, pts[20].y)),
                          {'nom': 'BACK LENGTH'}, 700.0),
        )
        return replace(doc, pieces=(replace(back, poms=poms),) + doc.pieces[1:])

    def test_la_capa_es_rellegeix_com_a_taula_de_poms(self):
        doc = self._amb_poms()
        tornat = AAMAReader().read(
            AAMAWriter().write(doc, include_ftt_pom_layer=True,
                               ftt_meta={'versio': 3, 'model': 'BRW-26-SS-0002'})
        )
        poms = tornat.piece('BACK').poms
        self.assertEqual([p.pom_code for p in poms], ['POM-001', 'POM-014'])
        self.assertEqual(poms[0].valor_mesurat_mm, 525.0)
        self.assertEqual(poms[0].definicio_mesura['nom'], 'CHEST WIDTH')

        # La geometria i els POMs han de tornar iguals. L'empremta NO: hi hem afegit una
        # capa a posta, i el comparador ho canta (i fa bé de cantar-ho).
        report = compare(doc, tornat, comparar_empremta=False)
        self.assertTrue(report.ok, report.resum())
        self.assertIn(FTT_POM_LAYER, tornat.fingerprint.capes_presents)

    def test_afegir_la_capa_es_una_diferencia_i_el_comparador_ho_diu(self):
        """L'eina no ha de callar ni quan el canvi és nostre i volgut."""
        doc = self._amb_poms()
        tornat = AAMAReader().read(AAMAWriter().write(doc, include_ftt_pom_layer=True))
        report = compare(doc, tornat)
        self.assertFalse(report.ok)
        self.assertEqual([d.tipus for d in report.diferencies], ['layers'])

    def test_sense_el_parametre_no_hi_ha_capa(self):
        """Un destí pot rebutjar una capa que no coneix: ha de poder rebre el fitxer sense."""
        escrit = AAMAWriter().write(self._amb_poms(), include_ftt_pom_layer=False)
        self.assertNotIn(FTT_POM_LAYER, escrit.decode())
        self.assertEqual(AAMAReader().read(escrit).piece('BACK').poms, ())

    def test_la_nostra_capa_no_es_una_capa_desconeguda(self):
        tornat = AAMAReader().read(
            AAMAWriter().write(self._amb_poms(), include_ftt_pom_layer=True)
        )
        self.assertIn(FTT_POM_LAYER, tornat.fingerprint.capes_presents)
        self.assertNotIn(FTT_POM_LAYER, tornat.fingerprint.capes_desconegudes)
        # I no s'ha guardat com a rastre literal: si no, es duplicaria en reexportar.
        capes_raw = {r.layer for r in tornat.piece('BACK').raw_entities}
        self.assertEqual(capes_raw, {'15'})

    def test_reexportar_no_engreixa_el_fitxer(self):
        """Quatre voltes seguides: el cens s'ha de quedar quiet.

        Si el FTT-META es confongués amb una metadada del CAD d'origen, el fitxer
        creixeria una línia per volta i ningú no se n'adonaria fins molt tard.
        """
        doc = self._amb_poms()
        censos = []
        for volta in range(4):
            doc = AAMAReader().read(
                AAMAWriter().write(doc, include_ftt_pom_layer=True,
                                   ftt_meta={'versio': volta})
            )
            censos.append(doc.fingerprint.cens_entitats)
        self.assertEqual(censos[0], censos[-1])
        self.assertEqual([p.pom_code for p in doc.piece('BACK').poms],
                         ['POM-001', 'POM-014'])


class ReplegatDoblecTest(unittest.TestCase):
    """Desplegar i tornar a plegar ha de deixar la peça com estava."""

    def test_cicle_complet_recupera_la_geometria(self):
        doc = AAMAReader().read(mitja_peca_dxf())
        mitja = doc.piece('MITJA')
        sencera = unfold_piece(mitja)
        replegada = fold_piece(sencera)

        a = mitja.boundary(LayerRole.CUT).points
        b = replegada.boundary(LayerRole.CUT).points
        self.assertEqual(len(a), len(b))
        for pa, pb in zip(a, b):
            self.assertAlmostEqual(pa.x, pb.x, places=9)
            self.assertAlmostEqual(pa.y, pb.y, places=9)
            self.assertIs(pa.kind, pb.kind)
        self.assertEqual(len(mitja.notches), len(replegada.notches))
        self.assertFalse(replegada.doblec_original.materialitzat)

    def test_el_costat_es_fixa_en_detectar_no_despres(self):
        """Un cop desplegada, la peça té punts als dos costats i ja no hi ha manera de
        saber quin era l'original: per això el costat es guarda en detectar el doblec."""
        mitja = AAMAReader().read(mitja_peca_dxf()).piece("MITJA")
        self.assertNotEqual(mitja.doblec_original.costat, 0)
        self.assertEqual(unfold_piece(mitja).doblec_original.costat,
                         mitja.doblec_original.costat)

    def test_plegar_una_peca_no_desplegada_no_la_toca(self):
        back = AAMAReader().read(AMELIA_DXF.read_bytes()).piece('BACK')
        self.assertIs(fold_piece(back), back)


class ComparadorTest(unittest.TestCase):
    """L'eina no pot donar verd per construcció: ha de saber dir que no."""

    @classmethod
    def setUpClass(cls):
        cls.doc = AAMAReader().read(AMELIA_DXF.read_bytes())

    def _mou_un_punt(self, doc, delta_mm: float):
        pieces = list(doc.pieces)
        p = pieces[0]
        bs = list(p.boundaries)
        v = bs[0]
        pts = list(v.points)
        pts[5] = replace(pts[5], x=pts[5].x + delta_mm)
        bs[0] = replace(v, points=tuple(pts))
        pieces[0] = replace(p, boundaries=tuple(bs))
        return replace(doc, pieces=tuple(pieces))

    def test_detecta_un_punt_mogut_1_mm(self):
        report = compare(self.doc, self._mou_un_punt(self.doc, 1.0))
        self.assertFalse(report.ok)
        self.assertEqual(report.diferencies[0].tipus, 'point_moved')
        self.assertAlmostEqual(report.desviacio_maxima_um, 1000.0)

    def test_detecta_fins_i_tot_2_micres(self):
        report = compare(self.doc, self._mou_un_punt(self.doc, 0.002))
        self.assertFalse(report.ok)
        self.assertAlmostEqual(report.desviacio_maxima_um, 2.0)

    def test_la_tolerancia_serveix_dalguna_cosa(self):
        mutat = self._mou_un_punt(self.doc, 0.002)
        self.assertTrue(compare(self.doc, mutat, tol_um=10.0).ok)
        self.assertFalse(compare(self.doc, mutat, tol_um=1.0).ok)

    def test_detecta_una_peca_perduda(self):
        report = compare(self.doc, replace(self.doc, pieces=self.doc.pieces[:3]))
        self.assertFalse(report.ok)
        self.assertIn('piece_missing', [d.tipus for d in report.diferencies])

    def test_detecta_una_capa_menjada_pel_cad_del_mig(self):
        """El cas que la prova Montse ha de saber contestar."""
        pieces = list(self.doc.pieces)
        pieces[0] = replace(pieces[0], unknown_layers=(), raw_entities=())
        report = compare(self.doc, replace(self.doc, pieces=tuple(pieces)))
        self.assertFalse(report.ok)
        self.assertIn('unknown_layers', [d.tipus for d in report.diferencies])

    def test_detecta_un_pom_perdut_pel_cami(self):
        pts = self.doc.piece('BACK').boundary(LayerRole.CUT).points
        pom = POMAnchorData('POM-001', ((pts[0].x, pts[0].y), (pts[5].x, pts[5].y)),
                            {'nom': 'CHEST WIDTH'}, 525.0)
        amb = replace(self.doc,
                      pieces=(replace(self.doc.piece('BACK'), poms=(pom,)),) + self.doc.pieces[1:])
        report = compare(amb, self.doc)
        self.assertFalse(report.ok)
        self.assertIn('pom_lost', [d.tipus for d in report.diferencies])

    def test_el_resum_es_llegible(self):
        self.assertIn('✅', compare(self.doc, self.doc).resum())
        self.assertIn('❌', compare(self.doc, self._mou_un_punt(self.doc, 1.0)).resum())


# ═════════════════════════════════════════════════════════════════════════════
# S3 · PERSISTÈNCIA + API — el motor endollat a FTT
#
# Aquests SÍ que necessiten BD i tenant (TenantTestCase), a diferència dels de l'engine.
# La diferència no és un detall d'infraestructura: és la frontera hexagonal fent-se
# visible. Tot el que és motor es prova sense Django; tot el que és adaptador, amb.
# ═════════════════════════════════════════════════════════════════════════════

class PatternsAPITestBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tec', password='x')
        self.gt = GarmentType.objects.create(
            codi_client='GT1', nom_client='Garment 1', grup='tops')
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='item_a', name='Item A')
        self.model = Model.objects.create(
            codi_intern='QA-PAT-0001', codi_tenant='TST', any=2026,
            temporada='SS', sequencial=1,
        )
        self.factory = APIRequestFactory()

    def _upload(self, dxf_bytes=None, rul_bytes=None, **extra):
        dades = {'model': self.model.id}
        dades.update(extra)
        if dxf_bytes is not None:
            dades['fitxer_dxf'] = SimpleUploadedFile(
                'AMELIA.dxf', dxf_bytes, content_type='application/octet-stream')
        if rul_bytes is not None:
            dades['fitxer_rul'] = SimpleUploadedFile(
                'AMELIA.rul', rul_bytes, content_type='application/octet-stream')

        request = self.factory.post(
            '/api/v1/patterns/pattern-files/', dades, format='multipart')
        force_authenticate(request, user=self.user)
        view = PatternFileViewSet.as_view({'post': 'create'})
        return view(request)


class UploadTest(PatternsAPITestBase):
    """Pujar l'AMELIA real per l'API i comprovar que arriba sencera a la BD."""

    def test_upload_amelia_persisteix_el_cens_de_S0_B3(self):
        resp = self._upload(AMELIA_DXF.read_bytes(), AMELIA_RUL.read_bytes())
        self.assertEqual(resp.status_code, 201, resp.data)

        fp = PatternFile.objects.get(pk=resp.data['id'])
        self.assertEqual(fp.model_id, self.model.id)
        self.assertEqual(fp.versio, 1)
        self.assertTrue(fp.is_current)
        self.assertEqual(fp.font_cad, 'polypattern')
        self.assertEqual(fp.escala_mm, 1.0)
        self.assertEqual(fp.unitats_metode, 'geometry')
        self.assertEqual(fp.unitats_confianca, 'high')

        # El mateix cens que la diagnosi va fer a mà, ara vingut de la BD.
        self.assertEqual(fp.pieces.count(), 4)
        esperat = {'BACK': (28, 22, 42), 'FRONT': (38, 22, 86),
                   'BACK_LINI': (24, 10, 14), 'FRONT_LINI': (44, 12, 50)}
        for nom, (tall, turn, curve) in esperat.items():
            with self.subTest(peca=nom):
                peca = fp.pieces.get(nom_block=nom)
                punts = peca.points.filter(mena='vertex')
                self.assertEqual(punts.filter(boundary_index=0).count(), tall)
                self.assertEqual(punts.filter(tipus='turn').count(), turn)
                self.assertEqual(punts.filter(tipus='curve').count(), curve)
                self.assertEqual(peca.points.filter(mena='notch').count(), 2)
                self.assertFalse(peca.has_sew)
                self.assertEqual(peca.unknown_layers, ['15'])

        # El RUL germà, llegit i desat.
        self.assertTrue(fp.te_rul)
        self.assertEqual(fp.grade_table['talles'], ['XS', 'S', 'M', 'L', 'XL'])
        self.assertEqual(fp.grade_table['talla_base'], 'M')
        # DXF i RUL són germans de debò: cap avís de coherència.
        self.assertNotIn('avisos_coherencia', resp.data)

    def test_upload_sense_rul(self):
        resp = self._upload(AMELIA_DXF.read_bytes())
        self.assertEqual(resp.status_code, 201)
        fp = PatternFile.objects.get(pk=resp.data['id'])
        self.assertFalse(fp.te_rul)
        self.assertIsNone(fp.grade_table)

    def test_rul_dun_altre_model_avisa_pero_no_bloqueja(self):
        """El DXF i el RUL viatgen junts, però ningú no garanteix que siguin germans."""
        rul_estrany = AMELIA_RUL.read_bytes().replace(b'SAMPLE SIZE:M', b'SAMPLE SIZE:L')
        resp = self._upload(AMELIA_DXF.read_bytes(), rul_estrany)
        self.assertEqual(resp.status_code, 201)
        codis = [a['codi'] for a in resp.data['avisos_coherencia']]
        self.assertIn('size_mismatch', codis)

    def test_fitxer_corrupte_es_422_amb_detall_mai_500(self):
        resp = self._upload(b'aixo no es un dxf' * 50)
        self.assertEqual(resp.status_code, 422)
        self.assertIn('error', resp.data)
        self.assertEqual(resp.data['issues'][0]['codi'], 'corrupt_dxf')
        self.assertEqual(PatternFile.objects.count(), 0)

    def test_extensio_no_permesa(self):
        dades = {
            'model': self.model.id,
            'fitxer_dxf': SimpleUploadedFile('virus.exe', b'MZ', content_type='x'),
        }
        request = self.factory.post('/api/v1/patterns/pattern-files/', dades, format='multipart')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(resp.status_code, 400)

    def test_cal_estar_autenticat(self):
        request = self.factory.post('/api/v1/patterns/pattern-files/', {}, format='multipart')
        resp = PatternFileViewSet.as_view({'post': 'create'})(request)
        self.assertIn(resp.status_code, (401, 403))


class SobiraniaTest(PatternsAPITestBase):
    """El XOR: un patró penja d'un Model O d'un ítem, mai de tots dos ni de cap."""

    def test_sense_propietari_es_400(self):
        dades = {'fitxer_dxf': SimpleUploadedFile('a.dxf', AMELIA_DXF.read_bytes())}
        request = self.factory.post('/api/v1/patterns/pattern-files/', dades, format='multipart')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(resp.status_code, 400)

    def test_amb_els_dos_propietaris_es_400(self):
        resp = self._upload(AMELIA_DXF.read_bytes(), garment_type_item=self.item.id)
        self.assertEqual(resp.status_code, 400)

    def test_la_bd_tambe_ho_impedeix_encara_que_algu_es_salti_la_view(self):
        """El constraint no és decoració: és l'última línia."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatternFile.objects.create(nom_fitxer='x.dxf')  # ni model ni ítem

    def test_patro_de_biblioteca_penjat_dun_item(self):
        dades = {
            'garment_type_item': self.item.id,
            'fitxer_dxf': SimpleUploadedFile('a.dxf', AMELIA_DXF.read_bytes()),
        }
        request = self.factory.post('/api/v1/patterns/pattern-files/', dades, format='multipart')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(resp.status_code, 201)
        fp = PatternFile.objects.get(pk=resp.data['id'])
        self.assertIsNone(fp.model_id)
        self.assertEqual(fp.garment_type_item_id, self.item.id)


class CadenaDeVersionsTest(PatternsAPITestBase):

    def test_encadenar_una_versio_apaga_el_cap_anterior(self):
        v1 = PatternFile.objects.get(pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])
        resp = self._upload(AMELIA_DXF.read_bytes(), versio_anterior_id=v1.id)
        self.assertEqual(resp.status_code, 201)

        v2 = PatternFile.objects.get(pk=resp.data['id'])
        v1.refresh_from_db()
        self.assertEqual(v2.versio, 2)
        self.assertTrue(v2.is_current)
        self.assertFalse(v1.is_current)
        self.assertEqual(v2.versio_anterior_id, v1.id)

    def test_bifurcar_una_cadena_es_409(self):
        """Un fitxer no pot tenir dos futurs. La view ho diu abans que la BD hi arribi."""
        v1 = PatternFile.objects.get(pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])
        self._upload(AMELIA_DXF.read_bytes(), versio_anterior_id=v1.id)

        resp = self._upload(AMELIA_DXF.read_bytes(), versio_anterior_id=v1.id)
        self.assertEqual(resp.status_code, 409)
        self.assertIn('bifurcar', resp.data['error'])

    def test_i_la_bd_ho_impediria_igualment(self):
        v1 = PatternFile.objects.get(pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])
        PatternFile.objects.create(
            model=self.model, nom_fitxer='v2.dxf', versio=2, versio_anterior=v1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatternFile.objects.create(
                    model=self.model, nom_fitxer='v2b.dxf', versio=2, versio_anterior=v1)


class AdapterRoundtripTest(PatternsAPITestBase):
    """dataclasses → ORM → dataclasses. Si una traducció perd un camp, el comparador
    de S2 el troba a faltar: és el mateix que valida el round-trip dels fitxers."""

    def test_el_viatge_danada_i_tornada_no_perd_res(self):
        original = AAMAReader().read(AMELIA_DXF.read_bytes())

        fp = PatternFile.objects.create(model=self.model, nom_fitxer='a.dxf')
        store = DjangoGeometryStore()
        store.save(original, pattern_file=fp)
        tornat = store.load(fp.id)

        report = compare(original, tornat)
        self.assertTrue(report.ok, report.resum())
        self.assertEqual(report.punts_comparats, 266)
        self.assertEqual(report.desviacio_maxima_um, 0.0)

    def test_lempremta_sobreviu_a_la_bd(self):
        """Sense empremta no hi ha reproducció: el fitxer exportat seria un DXF
        qualsevol, no el DXF d'aquest client."""
        original = AAMAReader().read(AMELIA_DXF.read_bytes())
        fp = save_pattern_file(model=self.model, dxf=_uploaded(AMELIA_DXF), document=original)
        DjangoGeometryStore().save(original, pattern_file=fp)

        tornat = DjangoGeometryStore().load(fp.id)
        self.assertEqual(tornat.fingerprint.font_cad, 'polypattern')
        self.assertEqual(tornat.fingerprint.capes_desconegudes, ('15',))
        self.assertEqual(tornat.fingerprint.separador_decimal,
                         {'coordenades': '.', 'text': ','})
        self.assertTrue(tornat.fingerprint.header_buida)

    def test_i_des_de_la_bd_es_pot_tornar_a_escriure_el_fitxer(self):
        """La prova de foc: BD → DXF → llegir → idèntic a l'original. És el que S7 farà."""
        original = AAMAReader().read(AMELIA_DXF.read_bytes())
        fp = save_pattern_file(model=self.model, dxf=_uploaded(AMELIA_DXF), document=original)
        DjangoGeometryStore().save(original, pattern_file=fp)

        des_de_bd = DjangoGeometryStore().load(fp.id)
        reescrit = AAMAReader().read(AAMAWriter().write(des_de_bd))
        self.assertTrue(compare(original, reescrit).ok, compare(original, reescrit).resum())


class RenderSVGTest(PatternsAPITestBase):

    def _fp(self):
        return PatternFile.objects.get(pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])

    def _get_svg(self, fp, **params):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{fp.id}/render.svg/', params)
        force_authenticate(request, user=self.user)
        return PatternFileViewSet.as_view({'get': 'render_svg'})(request, pk=fp.id)

    def test_el_svg_es_xml_valid_amb_un_path_per_vora(self):
        resp = self._get_svg(self._fp())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'image/svg+xml')

        arrel = ElementTree.fromstring(resp.content)  # peta si no és XML vàlid
        ns = '{http://www.w3.org/2000/svg}'
        self.assertTrue(arrel.tag.endswith('svg'))
        grups = arrel.findall(f'{ns}g')
        self.assertEqual([g.get('id') for g in grups],
                         ['BACK', 'FRONT', 'BACK_LINI', 'FRONT_LINI'])
        self.assertTrue(arrel.findall(f'.//{ns}path'))

    def test_una_sola_peca(self):
        resp = self._get_svg(self._fp(), piece='BACK')
        arrel = ElementTree.fromstring(resp.content)
        ns = '{http://www.w3.org/2000/svg}'
        self.assertEqual([g.get('id') for g in arrel.findall(f'{ns}g')], ['BACK'])

    def test_una_peca_que_no_existeix_no_peta(self):
        resp = self._get_svg(self._fp(), piece='NO_EXISTEIX')
        self.assertEqual(resp.status_code, 200)
        ElementTree.fromstring(resp.content)

    # ── X1 — el fons, que com a imatge no es veu, vectoritzat tapava la fitxa sencera ──
    def _rects_de_fons(self, resp):
        ns = '{http://www.w3.org/2000/svg}'
        return ElementTree.fromstring(resp.content).findall(f'{ns}rect')

    def test_per_defecte_el_fons_hi_es(self):
        """Qui l'ensenya com a IMATGE el necessita: un patró sobre transparent no es llegeix."""
        self.assertEqual(len(self._rects_de_fons(self._get_svg(self._fp()))), 1)

    def test_amb_fons_0_no_hi_ha_rectangle_de_fons(self):
        """Vectoritzat no hi ha viewBox que retalli: el fons deixaria de ser fons i seria una
        forma blanca opaca de 200000×200000 mm sobre la pàgina."""
        resp = self._get_svg(self._fp(), fons='0')
        self.assertEqual(self._rects_de_fons(resp), [])
        arrel = ElementTree.fromstring(resp.content)
        ns = '{http://www.w3.org/2000/svg}'
        # El dibuix hi és sencer: es treu el fons, no la peça.
        self.assertTrue(arrel.findall(f'.//{ns}path'))

    def test_el_viewbox_no_depen_del_fons(self):
        """El marc (i per tant l'aspecte amb què entra a la fitxa) ha de ser idèntic."""
        amb = ElementTree.fromstring(self._get_svg(self._fp(), piece='BACK').content)
        sense = ElementTree.fromstring(self._get_svg(self._fp(), piece='BACK', fons='0').content)
        self.assertEqual(amb.get('viewBox'), sense.get('viewBox'))


class GeometryEndpointTest(PatternsAPITestBase):
    """El que el visor Konva dibuixa. A diferència del detall (que dona RECOMPTES),
    aquí hi ha d'haver cada coordenada."""

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])

    def _geometry(self):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/geometry/')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'get': 'geometry'})(request, pk=self.fp.id)
        self.assertEqual(resp.status_code, 200)
        return resp.data

    def test_les_coordenades_hi_son_totes(self):
        """El cens de S0-B3, ara comptat sobre els punts que arriben al navegador."""
        dades = self._geometry()
        self.assertEqual(dades['escala_mm'], 1.0)
        self.assertEqual(len(dades['pieces']), 4)

        esperat = {'BACK': (28, 22, 42), 'FRONT': (38, 22, 86),
                   'BACK_LINI': (24, 10, 14), 'FRONT_LINI': (44, 12, 50)}
        for peca in dades['pieces']:
            with self.subTest(peca=peca['nom_block']):
                tall, turn, curve = esperat[peca['nom_block']]
                vores = {b['role']: b for b in peca['boundaries']}
                self.assertEqual(len(vores['cut']['points']), tall)
                self.assertTrue(vores['cut']['closed'])

                tots = [p for b in peca['boundaries'] for p in b['points']]
                self.assertEqual(sum(1 for p in tots if p['tipus'] == 'turn'), turn)
                self.assertEqual(sum(1 for p in tots if p['tipus'] == 'curve'), curve)
                self.assertEqual(len(peca['notches']), 2)
                self.assertIsNotNone(peca['grain'])
                self.assertFalse(peca['has_sew'])

    def test_els_punts_venen_en_ordre(self):
        """L'ordre dins la vora ÉS el contorn: perdre'l vol dir dibuixar un garbuix.

        Es comprova contra la font: la seqüència que arriba al navegador ha de ser
        EXACTAMENT la que el motor va llegir del fitxer. Sense llindars de distància —
        un contorn real té arestes llargues legítimes (a la BACK n'hi ha una de 385 mm) i
        qualsevol llindar seria un número inventat que tant deixaria passar un ordre
        barrejat com suspendria un contorn correcte.
        """
        del_motor = AAMAReader().read(AMELIA_DXF.read_bytes())
        cut_motor = del_motor.piece('BACK').boundary(LayerRole.CUT)

        dades = self._geometry()
        back = next(p for p in dades['pieces'] if p['nom_block'] == 'BACK')
        cut_api = next(b for b in back['boundaries'] if b['role'] == 'cut')

        self.assertEqual(len(cut_api['points']), len(cut_motor.points))
        for i, (api, motor) in enumerate(zip(cut_api['points'], cut_motor.points)):
            with self.subTest(punt=i):
                self.assertAlmostEqual(api['x'], motor.x, places=6)
                self.assertAlmostEqual(api['y'], motor.y, places=6)
                self.assertEqual(api['tipus'], motor.kind.value)

    def test_la_regla_de_grading_arriba_al_visor(self):
        dades = self._geometry()
        back = next(p for p in dades['pieces'] if p['nom_block'] == 'BACK')
        tots = [p for b in back['boundaries'] for p in b['points']]
        turn = [p for p in tots if p['tipus'] == 'turn']
        curve = [p for p in tots if p['tipus'] == 'curve']
        self.assertTrue(all(p['grade_rule_num'] == 1 for p in turn))
        self.assertTrue(all(p['grade_rule_num'] is None for p in curve))

    def test_cal_estar_autenticat(self):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/geometry/')
        resp = PatternFileViewSet.as_view({'get': 'geometry'})(request, pk=self.fp.id)
        self.assertIn(resp.status_code, (401, 403))


class DescarregaTest(PatternsAPITestBase):

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(pk=self._upload(
            AMELIA_DXF.read_bytes(), AMELIA_RUL.read_bytes()).data['id'])

    def _signed(self, pk, token, accio='download_signed', url='download-signed'):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{pk}/{url}/', {'token': token})
        return PatternFileViewSet.as_view({'get': accio})(request, pk=pk)

    def test_token_valid(self):
        token = signing.dumps(self.fp.id, salt=PATTERN_DOWNLOAD_SALT)
        self.assertEqual(self._signed(self.fp.id, token).status_code, 200)

    def test_token_dolent(self):
        self.assertEqual(self._signed(self.fp.id, 'inventat').status_code, 403)

    def test_token_caducat(self):
        token = signing.dumps(self.fp.id, salt=PATTERN_DOWNLOAD_SALT)
        with mock.patch('django.core.signing.time.time', return_value=time.time() + 901):
            self.assertEqual(self._signed(self.fp.id, token).status_code, 403)

    def test_el_token_dun_altre_model_NO_val_aqui(self):
        """La raó de tenir salts separats. Amb un salt compartit, un token emès per al
        ModelFitxer id=5 obriria el PatternFile id=5."""
        token_alie = signing.dumps(self.fp.id, salt=MODEL_FITXER_SALT)
        self.assertEqual(self._signed(self.fp.id, token_alie).status_code, 403)

    def test_el_token_del_dxf_no_obre_el_rul(self):
        """Dos artefactes, dos salts: el mateix raonament, un nivell més avall."""
        token_dxf = signing.dumps(self.fp.id, salt=PATTERN_DOWNLOAD_SALT)
        resp = self._signed(self.fp.id, token_dxf,
                            accio='download_rul_signed', url='download-rul-signed')
        self.assertEqual(resp.status_code, 403)

    def test_el_token_del_rul_si_obre_el_rul(self):
        token_rul = signing.dumps(self.fp.id, salt=PATTERN_RUL_DOWNLOAD_SALT)
        resp = self._signed(self.fp.id, token_rul,
                            accio='download_rul_signed', url='download-rul-signed')
        self.assertEqual(resp.status_code, 200)

    def test_esborrar_neteja_els_bytes_dels_dos_artefactes(self):
        dxf_path = self.fp.fitxer_dxf.name
        rul_path = self.fp.fitxer_rul.name
        self.assertTrue(default_storage.exists(dxf_path))
        self.assertTrue(default_storage.exists(rul_path))

        request = self.factory.delete(f'/api/v1/patterns/pattern-files/{self.fp.id}/')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'delete': 'destroy'})(request, pk=self.fp.id)
        self.assertEqual(resp.status_code, 204)

        self.assertFalse(default_storage.exists(dxf_path))
        self.assertFalse(default_storage.exists(rul_path))
        self.assertEqual(PatternFile.objects.count(), 0)


# ═════════════════════════════════════════════════════════════════════════════
# S6 · ANOTACIÓ — segments, mesures i costures
# ═════════════════════════════════════════════════════════════════════════════

class SegmentacioTest(unittest.TestCase):
    """De gir a gir sobre el contorn de tall. Engine pur."""

    @classmethod
    def setUpClass(cls):
        cls.doc = AAMAReader().read(AMELIA_DXF.read_bytes())

    def test_els_segments_sumen_el_perimetre(self):
        """La prova que no es pot falsejar: si un tram falta o es compta dos cops, la
        suma no dona el perímetre."""
        esperat = {'BACK': 14, 'FRONT': 10, 'BACK_LINI': 10, 'FRONT_LINI': 8}
        for piece in self.doc.pieces:
            with self.subTest(peca=piece.nom_block):
                segs = segmentar_peca(piece)
                self.assertEqual(len(segs), esperat[piece.nom_block])
                cut = piece.boundary(LayerRole.CUT)
                self.assertAlmostEqual(
                    sum(s.longitud_mm for s in segs), longitud_vora(cut), places=6)

    def test_hi_ha_un_segment_per_gir(self):
        """En una vora tancada, N girs → N trams."""
        for piece in self.doc.pieces:
            with self.subTest(peca=piece.nom_block):
                cut = piece.boundary(LayerRole.CUT)
                girs = sum(1 for p in cut.points if p.kind is PointKind.TURN)
                self.assertEqual(len(segmentar_peca(piece)), girs)

    def test_els_parametres_van_de_0_a_1(self):
        for piece in self.doc.pieces:
            segs = segmentar_peca(piece)
            self.assertAlmostEqual(segs[0].t_inici, 0.0, places=9)
            self.assertAlmostEqual(segs[-1].t_fi, 1.0, places=6)
            for a, b in zip(segs, segs[1:]):
                self.assertAlmostEqual(a.t_fi, b.t_inici, places=9)

    def test_una_vora_sense_cap_gir_es_un_sol_tram(self):
        """Un cercle no té cantonades, i tot i així s'hi ha de poder ancorar una costura.
        Tornar zero trams el deixaria fora de tot."""
        punts = tuple(
            PointData(x=math.cos(a) * 100, y=math.sin(a) * 100, kind=PointKind.CURVE)
            for a in [i * math.pi / 6 for i in range(12)]
        )
        vora = BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=True)
        segs = segmentar_vora(vora, 0)
        self.assertEqual(len(segs), 1)
        self.assertAlmostEqual(segs[0].t_inici, 0.0)
        self.assertAlmostEqual(segs[0].t_fi, 1.0)


class TramsNaturalsTest(unittest.TestCase):
    """La vora llegida com l'ofici la llegeix. Engine pur, material real (AMELIA)."""

    @classmethod
    def setUpClass(cls):
        cls.doc = AAMAReader().read(AMELIA_DXF.read_bytes())

    def test_els_naturals_sumen_el_perimetre(self):
        """La mateixa prova que no es pot falsejar que als AUTO: fusionar no pot perdre
        ni duplicar vora. Si un natural es menja un tros de més, la suma no dona."""
        for piece in self.doc.pieces:
            with self.subTest(peca=piece.nom_block):
                nats = segmentar_peca_natural(piece)
                cut = piece.boundary(LayerRole.CUT)
                self.assertAlmostEqual(
                    sum(s.longitud_mm for s in nats), longitud_vora(cut), places=6)

    def test_l_amelia_surt_amb_quatre_costures_per_peca(self):
        """El calibratge (T1b) sobre material real: l'AMELIA té 4 cantonades per peça, i
        el CAD n'hi marca fins a 14. Aquest número el va mirar un humà."""
        for piece in self.doc.pieces:
            with self.subTest(peca=piece.nom_block):
                self.assertEqual(len(segmentar_peca_natural(piece)), 4)

    def test_els_naturals_son_menys_que_els_auto_i_no_els_toquen(self):
        """Els naturals són una VISTA: no substitueixen els AUTO, que segueixen igual."""
        for piece in self.doc.pieces:
            with self.subTest(peca=piece.nom_block):
                auto = segmentar_peca(piece)
                nat = segmentar_peca_natural(piece)
                self.assertLess(len(nat), len(auto))
                self.assertAlmostEqual(
                    sum(s.longitud_mm for s in auto),
                    sum(s.longitud_mm for s in nat), places=6)

    def test_el_llindar_te_una_meseta(self):
        """T1b: entre 20° i 25° el resultat no es mou. Si algú toca el llindar i això peta,
        és que el material ha canviat i cal recalibrar, no ajustar el número a ull."""
        for piece in self.doc.pieces:
            for llindar in (20.0, 22.0, 25.0):
                with self.subTest(peca=piece.nom_block, llindar=llindar):
                    self.assertEqual(
                        len(segmentar_peca_natural(piece, llindar_graus=llindar)), 4)

    def test_una_corba_suau_no_talla(self):
        """Dotze girs en cercle: el CAD els marca tots, però cap no és cantonada. Un coll
        rodó és UNA costura."""
        punts = tuple(
            PointData(x=math.cos(a) * 100, y=math.sin(a) * 100, kind=PointKind.TURN)
            for a in [i * math.pi / 6 for i in range(12)]
        )
        vora = BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=True)
        peca = PieceData(nom_block='C', boundaries=(vora,))
        # Cada gir desvia 30°: per sobre del llindar, dotze trams; per sota, un de sol.
        self.assertEqual(len(segmentar_vora_natural(peca, vora, 0, llindar_graus=22.0)), 12)
        self.assertEqual(len(segmentar_vora_natural(peca, vora, 0, llindar_graus=45.0)), 1)

    def test_el_piquet_no_talla(self):
        """La peça que sosté el mòdul. Una excursió de piquet en V té girs de ~60° —més
        forts que cantonades de debò— i, si tallessin, partirien la costura en tres."""
        # Una L: recta llarga cap a l'est amb un dent de piquet al mig, i una cantonada.
        punts = (
            PointData(x=0, y=0, kind=PointKind.TURN),        # cantonada d'inici
            PointData(x=100, y=0, kind=PointKind.TURN),      # pota del piquet
            PointData(x=110, y=8, kind=PointKind.TURN),      # pic del piquet
            PointData(x=120, y=0, kind=PointKind.TURN),      # pota del piquet
            PointData(x=300, y=0, kind=PointKind.TURN),      # cantonada
            PointData(x=300, y=200, kind=PointKind.TURN),    # cantonada
        )
        vora = BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=True)
        sense = PieceData(nom_block='P', boundaries=(vora,))
        amb = PieceData(nom_block='P', boundaries=(vora,), notches=(
            NotchData(x=100, y=0), NotchData(x=120, y=0),
        ))
        # Sense declarar els piquets, els seus girs passen per cantonades i esmicolen la vora.
        self.assertIn(2, cantonades_naturals(sense, vora))
        # Declarats, l'excursió sencera queda fora: la recta 0→300 és UNA costura.
        self.assertEqual(vertexs_de_piquet(amb, vora), {1, 2, 3})
        cant = cantonades_naturals(amb, vora)
        self.assertNotIn(1, cant)
        self.assertNotIn(2, cant)
        self.assertNotIn(3, cant)
        self.assertEqual(cant, [0, 4, 5])

    def test_el_piquet_viatja_dins_del_tram_com_a_metadada(self):
        """No tallar no vol dir ignorar: A2 llegeix els piquets per inferir frunzit."""
        punts = (
            PointData(x=0, y=0, kind=PointKind.TURN),
            PointData(x=100, y=0, kind=PointKind.TURN),
            PointData(x=110, y=8, kind=PointKind.TURN),
            PointData(x=120, y=0, kind=PointKind.TURN),
            PointData(x=300, y=0, kind=PointKind.TURN),
            PointData(x=300, y=200, kind=PointKind.TURN),
        )
        vora = BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=True)
        peca = PieceData(nom_block='P', boundaries=(vora,), notches=(
            NotchData(x=100, y=0), NotchData(x=120, y=0),
        ))
        nats = segmentar_vora_natural(peca, vora, 0)
        primer = next(s for s in nats if s.index_inici == 0)
        self.assertEqual(len(primer.piquets), 2)
        # I diu de quins girs surt: la fusió ha de ser auditable.
        self.assertEqual(primer.girs_fusionats, (1, 2, 3))

    def test_els_extrems_de_pinca_tallen_encara_que_l_angle_no(self):
        """Una pinça declarada parteix la vora encara que hi arribi suau: el que hi ha a
        banda i banda són dues costures diferents, i això és domini, no geometria."""
        punts = tuple(
            PointData(x=math.cos(a) * 100, y=math.sin(a) * 100, kind=PointKind.CURVE)
            for a in [i * math.pi / 6 for i in range(12)]
        )
        vora = BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=True)
        peca = PieceData(nom_block='C', boundaries=(vora,))
        self.assertEqual(len(segmentar_vora_natural(peca, vora, 0)), 1)
        amb_pinca = segmentar_vora_natural(peca, vora, 0, talls_extra=(3, 6))
        self.assertEqual(len(amb_pinca), 2)
        self.assertEqual([s.index_inici for s in amb_pinca], [3, 6])

    def test_la_desviacio_no_es_deixa_enganyar_per_vertexs_duplicats(self):
        """Els fitxers reals repeteixen punts. Un vèrtex duplicat no defineix direcció i
        no pot ser cantonada de res."""
        pts = (PointData(x=0, y=0), PointData(x=0, y=0), PointData(x=10, y=0))
        self.assertEqual(desviacio_angular(pts, 1, closed=True), 0.0)
        self.assertEqual(desviacio_angular(pts, 1, closed=False), 0.0)
        # I l'extrem d'una vora oberta sí que és frontera per definició.
        self.assertEqual(desviacio_angular(pts, 0, closed=False), 180.0)


class PreferenciaSenyalTest(unittest.TestCase):
    """El costum del taller com a senyal. Engine pur: sense BD, amb números inventats."""

    def _c(self, nom, pref='', **kw):
        return Candidat(
            segment_id=kw.get('sid', 1), piece_id=1, piece_nom=nom, vora=0,
            t_inici=0.0, t_fi=0.5, longitud_mm=500.0, preferencia=pref)

    def test_els_dos_costats_confirmats_pesen_el_doble_que_un(self):
        un = senyal_preferencia(self._c('A', 'confirmat'), self._c('B'))
        dos = senyal_preferencia(self._c('A', 'confirmat'), self._c('B', 'confirmat'))
        self.assertAlmostEqual(un.punts, PES_PREFERENCIA * 0.5)
        self.assertAlmostEqual(dos.punts, PES_PREFERENCIA)

    def test_sense_costum_el_senyal_no_diu_res(self):
        self.assertEqual(senyal_preferencia(self._c('A'), self._c('B')).punts, 0.0)

    def test_un_costum_mut_no_embruta_el_desglos(self):
        """Sense res après, la proposta porta els tres senyals de sempre i cap més: una fila
        de zero punts i sense frase no es pot discutir."""
        a = Candidat(segment_id=1, piece_id=1, piece_nom='FRONT', vora=0, t_inici=0.0,
                     t_fi=0.5, longitud_mm=500.0, piquets=(0.25,))
        b = Candidat(segment_id=2, piece_id=2, piece_nom='BACK', vora=0, t_inici=0.0,
                     t_fi=0.5, longitud_mm=500.0, piquets=(0.25,))
        p = avaluar(a, b)
        self.assertIsNotNone(p)
        self.assertEqual({s.mena for s in p.senyals}, {'piquets', 'longitud', 'noms'})
        # I amb costum, hi surt.
        amb = avaluar(replace(a, preferencia='confirmat'), b)
        self.assertIn('preferencia', {s.mena for s in amb.senyals})

    def test_una_correccio_mana_sobre_una_confirmacio(self):
        """Si un costat s'ha corregit, que l'altre estigui confirmat no ho compensa: una
        costura amb un costat esmenat no és mitja bona."""
        s = senyal_preferencia(self._c('A', 'tallat'), self._c('B', 'confirmat'))
        self.assertAlmostEqual(s.punts, PES_PREFERENCIA_CONTRA)
        self.assertLess(s.punts, 0)

    def test_el_costum_NO_pot_habilitar_una_proposta_sense_geometria(self):
        """La llei del motor (W4): la geometria mana, i el costum ni tan sols acompanya —no
        entra a la porta. Dues peces sense cap evidència geomètrica no es proposen encara que
        el taller les hagi confirmat mil vegades; si ho fessin, el motor proposaria pel que la
        gent sol fer i repetiria els mals costums amb cada cop més confiança."""
        # Longituds incompatibles i cap piquet: geometria muda.
        a = Candidat(segment_id=1, piece_id=1, piece_nom='FRONT', vora=0, t_inici=0.0,
                     t_fi=0.5, longitud_mm=500.0, preferencia='confirmat')
        b = Candidat(segment_id=2, piece_id=2, piece_nom='BACK', vora=0, t_inici=0.0,
                     t_fi=0.5, longitud_mm=5000.0, preferencia='confirmat')
        self.assertIsNone(avaluar(a, b))

    def test_el_costum_pesa_menys_que_el_nom(self):
        """Ordre de pesos, escrit com a test: el costum diu menys sobre AQUEST patró que el
        nom, perquè descriu el que algú va fer en un ALTRE."""
        self.assertLess(PES_PREFERENCIA, PES_NOMS)
        self.assertLess(PES_PREFERENCIA, PES_LONGITUD)
        self.assertLess(PES_PREFERENCIA, PES_PIQUETS)


class PreferenciaAprenentatgeTest(PatternsAPITestBase):
    """Què s'aprèn i quan, amb el TATE real."""

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])
        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')
        self.nat = (self.front.segments
                    .filter(origen=PatternSegment.ORIGEN_NATURAL).order_by('-t_fi').first())

    def _declara(self, t_inici, t_fi, nom='QA'):
        return PatternSegment.objects.create(
            piece=self.front, vora=self.nat.vora, t_inici=t_inici, t_fi=t_fi,
            tipus_vora=self.nat.tipus_vora, origen=PatternSegment.ORIGEN_DECLARAT, nom=nom)

    def test_el_rol_no_col_lapsa_peces_diferents(self):
        """Al Tate el 'rol' del CAD és el nom sencer. Reduir-lo a un FRONT canònic faria que
        el que s'aprèn del davanter viatgés a la seva vista i al seu canesú."""
        rols = {rol_de_peca(p) for p in self.fp.pieces.all()}
        self.assertIn('TATE_FRONT', rols)
        self.assertIn('TATE_FRONT_FACING', rols)
        self.assertIn('TATE_FRONT_YOKE', rols)
        self.assertNotEqual(
            rol_de_peca(self.front),
            rol_de_peca(self.fp.pieces.get(nom_block='TATE_FRONT_FACING')))

    def test_confirmar_un_natural_tal_qual_s_apren_com_a_CONFIRMAT(self):
        pref = registra(self._declara(self.nat.t_inici, self.nat.t_fi))
        self.assertIsNotNone(pref)
        self.assertEqual(pref.accio, SegmentPreference.ACCIO_CONFIRMAT)
        self.assertEqual(pref.rol, 'TATE_FRONT')

    def test_re_confirmar_NO_duplica_la_fila_la_REFORCA(self):
        registra(self._declara(self.nat.t_inici, self.nat.t_fi))
        pref = registra(self._declara(self.nat.t_inici, self.nat.t_fi, nom='QA2'))
        self.assertEqual(SegmentPreference.objects.count(), 1)
        self.assertEqual(pref.vegades, 2)

    def test_escurcar_un_natural_s_apren_com_a_TALLAT(self):
        mig = self.nat.t_inici + (self.nat.t_fi - self.nat.t_inici) * 0.9
        pref = registra(self._declara(self.nat.t_inici, mig))
        self.assertIsNotNone(pref)
        self.assertEqual(pref.accio, SegmentPreference.ACCIO_TALLAT)

    def test_escurcar_molt_segueix_sent_una_correccio(self):
        """Declarar un tros petit d'un natural NO és un tram nou: és dir que aquell natural
        sencer no és el que es cus. Per això s'aprèn, i per això després baixa la proposta."""
        curt = self.nat.t_inici + (self.nat.t_fi - self.nat.t_inici) * 0.05
        pref = registra(self._declara(self.nat.t_inici, curt))
        self.assertIsNotNone(pref)
        self.assertEqual(pref.accio, SegmentPreference.ACCIO_TALLAT)

    def test_d_un_tram_que_CAVALCA_dues_lectures_no_se_n_apren_res(self):
        """Un tram a cavall de dos naturals no corregeix cap dels dos: no diu «aquest havia de
        ser més curt», diu una altra cosa. Inventar-li una preferència seria posar-li paraules
        a la boca."""
        naturals = list(self.front.segments
                        .filter(origen=PatternSegment.ORIGEN_NATURAL, vora=self.nat.vora)
                        .order_by('t_inici'))
        a, b = naturals[0], naturals[1]
        # De mig del primer a mig del segon: no cau dins de cap.
        mig_a = a.t_inici + (a.t_fi - a.t_inici) * 0.5
        mig_b = b.t_inici + (b.t_fi - b.t_inici) * 0.5
        self.assertIsNone(registra(self._declara(mig_a, mig_b)))

    def test_d_un_tram_DERIVAT_no_se_n_apren_res(self):
        """Només s'aprèn del «sí» humà. Un derivat no l'ha decidit ningú, i aprendre'n seria
        que el motor es donés la raó sol."""
        self.assertIsNone(registra(self.nat))

    def test_declarar_un_tram_per_l_API_ja_deixa_el_senyal(self):
        """El ganxo: el gest manual és un judici sobre la lectura, igual que confirmar una
        proposta. I no canvia res del que la crida feia abans."""
        punts = list(self.front.points.filter(
            mena='vertex', boundary_index=self.nat.vora).order_by('ordre'))
        a = next(p for p in punts if p.ordre == self.nat.index_inici) if hasattr(
            self.nat, 'index_inici') else punts[0]
        request = self.factory.post('/api/v1/patterns/pattern-segments/', {
            'point_a': punts[0].id, 'point_b': punts[4].id, 'nom': 'lateral',
        }, format='json')
        force_authenticate(request, user=self.user)
        resp = PatternSegmentViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(resp.status_code, 201, resp.data)


class MesuraTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = AAMAReader().read(AMELIA_DXF.read_bytes())
        cls.back = cls.doc.piece('BACK')
        cls.cut = cls.back.boundary(LayerRole.CUT)
        cls.punts = {i: p for i, p in enumerate(cls.cut.points)}
        cls.girs = [i for i, p in cls.punts.items() if p.kind is PointKind.TURN]

    def test_recta_i_vora_no_son_el_mateix(self):
        """Sobre els MATEIXOS dos punts, una cinta estirada i una cinta que resegueix la
        corba donen coses diferents. Per això el mètode es desa i no s'assumeix."""
        a, b = self.girs[0], self.girs[len(self.girs) // 2]
        recta = resoldre(self.back, {'mode': 'points', 'a': a, 'b': b}, self.punts, 'recta')
        vora = resoldre(self.back, {'mode': 'points', 'a': a, 'b': b}, self.punts, 'vora')
        self.assertAlmostEqual(recta.valor_cm, 51.29, places=1)
        self.assertAlmostEqual(vora.valor_cm, 117.71, places=1)
        self.assertGreater(vora.valor_cm, recta.valor_cm)

    def test_la_mesura_recta_es_la_distancia_euclidiana(self):
        a, b = self.girs[0], self.girs[1]
        pa, pb = self.punts[a], self.punts[b]
        esperat = math.hypot(pb.x - pa.x, pb.y - pa.y) / 10.0
        r = resoldre(self.back, {'mode': 'points', 'a': a, 'b': b}, self.punts)
        self.assertAlmostEqual(r.valor_cm, esperat, places=6)

    def test_landmark_es_un_punt_derivat_que_no_existeix(self):
        """'1 cm sota el punt de sisa': es calcula, no es materialitza. Si es
        materialitzés com a vèrtex, seria una còpia que envelliria."""
        a, b = self.girs[0], self.girs[2]
        base = resoldre(self.back, {'mode': 'points', 'a': a, 'b': b}, self.punts)
        derivat = resoldre(
            self.back,
            {'mode': 'landmark', 'landmark': a, 'offset_cm': 5.0, 'direccio': 'down', 'b': b},
            self.punts,
        )
        self.assertTrue(derivat.derivat)
        self.assertFalse(base.derivat)
        self.assertNotAlmostEqual(base.valor_cm, derivat.valor_cm, places=2)
        # El punt derivat no s'ha afegit a la geometria.
        self.assertEqual(len(self.back.boundary(LayerRole.CUT).points), 28)

    def test_una_recepta_que_apunta_a_un_punt_desaparegut_ho_diu(self):
        with self.assertRaises(MeasureError) as ctx:
            resoldre(self.back, {'mode': 'points', 'a': 9999, 'b': 0}, self.punts)
        self.assertIn('9999', str(ctx.exception))

    def test_mode_desconegut(self):
        with self.assertRaises(MeasureError):
            resoldre(self.back, {'mode': 'telepatia'}, self.punts)


class CosturaTest(unittest.TestCase):
    """El diferencial vol dir coses OPOSADES segons el tipus. És tot el test."""

    def test_casat_que_casa(self):
        c = validar(500.0, 500.0, 'casat')
        self.assertTrue(c.casa)
        self.assertEqual(c.desviament_cm, 0.0)

    def test_casat_que_no_casa_diu_quant(self):
        c = validar(530.0, 500.0, 'casat')
        self.assertFalse(c.casa)
        self.assertAlmostEqual(c.desviament_cm, 3.0)
        self.assertIn('3.0 cm', c.missatge)

    def test_un_casat_amb_diferencial_declarat_es_un_error_de_tipus(self):
        """Si un costat ha de sobrar, no és un casat. Val més dir-l'hi que fer-li cas."""
        c = validar(530.0, 500.0, 'casat', diferencial_cm=3.0)
        self.assertFalse(c.casa)
        self.assertIn('frunzit o una pinça', c.missatge)

    def test_frunzit_amb_el_diferencial_promes(self):
        """La MATEIXA diferència de 3 cm que suspèn un casat, aprova un frunzit."""
        c = validar(530.0, 500.0, 'frunzit', diferencial_cm=3.0)
        self.assertTrue(c.casa)
        self.assertAlmostEqual(c.desviament_cm, 0.0)
        self.assertIn('sobra 3.0 cm', c.missatge)

    def test_frunzit_que_no_compleix_el_que_prometia(self):
        c = validar(550.0, 500.0, 'frunzit', diferencial_cm=3.0)
        self.assertFalse(c.casa)
        self.assertAlmostEqual(c.desviament_cm, 2.0)

    def test_la_tolerancia_es_1_mm(self):
        self.assertTrue(validar(500.0, 500.9, 'casat').casa)
        self.assertFalse(validar(500.0, 502.0, 'casat').casa)


class AnotacioAPITest(PatternsAPITestBase):
    """POMs i costures per l'API, amb el material real."""

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])
        self.back = self.fp.pieces.get(nom_block='BACK')
        self.pom_master = POMMaster.objects.create(
            codi_client='CHEST', nom_client='Amplada de pit')
        self.girs = list(
            self.back.points.filter(mena='vertex', tipus='turn', boundary_index=0)
            .order_by('ordre'))

    def _ancora(self, a, b, pom=None, metode='recta'):
        request = self.factory.post('/api/v1/patterns/pattern-poms/', {
            'pattern_piece': self.back.id,
            'pom_master': (pom or self.pom_master).id,
            'definicio_mesura': {'mode': 'points', 'a': a.id, 'b': b.id},
            'metode': metode,
        }, format='json')
        force_authenticate(request, user=self.user)
        return PatternPOMViewSet.as_view({'post': 'create'})(request)

    def test_els_segments_es_deriven_en_importar(self):
        """No cal demanar-los: la peça ja ve amb les seves cantonades marcades pel CAD.

        Se'n deriven DUES lectures i totes dues es desen: la fina (`auto`, gir→gir) i la de
        l'ofici (`natural`, poques costures). Es compten per separat a posta —un total
        agregat passaria per bo el dia que una de les dues deixés de generar-se."""
        front = self.fp.pieces.get(nom_block='FRONT')
        for peca, auto, natural in ((self.back, 14, 4), (front, 10, 4)):
            with self.subTest(peca=peca.nom_block):
                self.assertEqual(
                    peca.segments.filter(origen=PatternSegment.ORIGEN_AUTO).count(), auto)
                self.assertEqual(
                    peca.segments.filter(origen=PatternSegment.ORIGEN_NATURAL).count(), natural)

    def test_ancorar_un_pom_el_mesura_al_servidor(self):
        resp = self._ancora(self.girs[0], self.girs[5])
        self.assertEqual(resp.status_code, 201, resp.data)

        pom = PatternPOM.objects.get(pk=resp.data['id'])
        self.assertIsNotNone(pom.valor_mesurat_cm)

        # El valor és exactament la distància entre els dos punts: no l'ha dit el client.
        a, b = self.girs[0], self.girs[5]
        esperat = round(math.hypot(b.x - a.x, b.y - a.y) / 10.0, 2)
        self.assertAlmostEqual(pom.valor_mesurat_cm, esperat, places=2)

    def test_el_client_no_pot_dictar_el_valor(self):
        """Encara que l'enviï, el servidor el sobreescriu amb el que diu la geometria."""
        request = self.factory.post('/api/v1/patterns/pattern-poms/', {
            'pattern_piece': self.back.id,
            'pom_master': self.pom_master.id,
            'definicio_mesura': {'mode': 'points', 'a': self.girs[0].id, 'b': self.girs[5].id},
            'valor_mesurat_cm': 999.0,          # ← mentida
        }, format='json')
        force_authenticate(request, user=self.user)
        resp = PatternPOMViewSet.as_view({'post': 'create'})(request)

        pom = PatternPOM.objects.get(pk=resp.data['id'])
        self.assertNotEqual(pom.valor_mesurat_cm, 999.0)

    def test_el_mateix_pom_dos_cops_a_la_mateixa_peca_rebota(self):
        self.assertEqual(self._ancora(self.girs[0], self.girs[5]).status_code, 201)
        segon = self._ancora(self.girs[1], self.girs[6])
        self.assertEqual(segon.status_code, 400)

    def test_no_es_pot_esborrar_un_POMMaster_ancorat(self):
        """PROTECT: la geometria en depèn. (A la BD el FK és DEFERRABLE, així que qui ho
        fa complir de debò és l'ORM — i per això es prova aquí i no a psql.)"""
        self._ancora(self.girs[0], self.girs[5])
        with self.assertRaises(ProtectedError):
            self.pom_master.delete()

    def test_la_geometria_serveix_els_poms_ancorats(self):
        self._ancora(self.girs[0], self.girs[5])
        request = self.factory.get(f'/api/v1/patterns/pattern-files/{self.fp.id}/geometry/')
        force_authenticate(request, user=self.user)
        dades = PatternFileViewSet.as_view({'get': 'geometry'})(request, pk=self.fp.id).data

        back = next(p for p in dades['pieces'] if p['nom_block'] == 'BACK')
        self.assertEqual(len(back['poms']), 1)
        self.assertEqual(back['poms'][0]['pom_code'], 'CHEST')
        self.assertEqual(
            len([s for s in back['segments'] if s['origen'] == PatternSegment.ORIGEN_AUTO]), 14)

    # ── costures ─────────────────────────────────────────────────────────────
    def _costura(self, segs_a, segs_b, tipus='casat', dif=0.0):
        request = self.factory.post('/api/v1/patterns/sew-relations/', {
            'model': self.model.id,
            'segments_a': [s.id for s in segs_a],
            'segments_b': [s.id for s in segs_b],
            'tipus': tipus,
            'diferencial_cm': dif,
        }, format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'create'})(request)

    def test_una_costura_dun_tram_amb_ell_mateix_sempre_casa(self):
        """El cas trivial que ha de sortir verd: si no, la longitud està mal calculada."""
        seg = self.back.segments.first()
        resp = self._costura([seg], [seg])
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(resp.data['estat']['casa'])
        self.assertAlmostEqual(
            resp.data['estat']['longitud_a_cm'], resp.data['estat']['longitud_b_cm'])

    def test_una_costura_de_trams_diferents_no_casa_i_diu_quant(self):
        segs = list(self.back.segments.all()[:2])
        resp = self._costura([segs[0]], [segs[1]])
        self.assertEqual(resp.status_code, 201)
        estat = resp.data['estat']
        self.assertFalse(estat['casa'])
        self.assertGreater(estat['desviament_cm'], 0)
        self.assertIn('NO casa', estat['missatge'])

    def test_un_frunzit_amb_el_diferencial_correcte_casa(self):
        """La mateixa parella de trams que suspèn com a casat, aprova com a frunzit si el
        diferencial declarat és el que de debò els separa."""
        segs = list(self.back.segments.all()[:2])
        dolent = self._costura([segs[0]], [segs[1]])
        diferencia = abs(dolent.data['estat']['diferencia_cm'])

        bo = self._costura([segs[0]], [segs[1]], tipus='frunzit', dif=diferencia)
        self.assertTrue(bo.data['estat']['casa'], bo.data['estat']['missatge'])

    def test_un_costat_pot_ser_la_suma_de_dos_trams(self):
        """Una màniga es cus contra una sisa que és davanter + esquena."""
        a = list(self.back.segments.all()[:2])
        front = self.fp.pieces.get(nom_block='FRONT')
        b = list(front.segments.all()[:1])
        resp = self._costura(a, b)
        self.assertEqual(resp.status_code, 201)
        suma = sum(s.t_fi - s.t_inici for s in a)
        self.assertGreater(resp.data['estat']['longitud_a_cm'], 0)
        self.assertGreater(suma, 0)


# ═════════════════════════════════════════════════════════════════════════════
# Guard de puresa — la frontera hexagonal, feta complir per una màquina
# ═════════════════════════════════════════════════════════════════════════════

class PurityGuardTest(unittest.TestCase):
    """`engine/` és un paquet Python pur i ho ha de continuar sent.

    La frontera hexagonal no s'esfondra d'un cop: s'esfondra el dia que algú necessita
    `timezone.now()` dins del motor i fa un import "petit". Aquest test és el que fa
    que aquell dia el sprint es posi vermell.

    Dos controls, perquè un de sol no basta: l'AST enxampa l'import escrit, i el
    subprocés enxampa el que arriba per una porta del darrere (un import transitiu que
    acabi carregant Django).
    """

    ENGINE = Path(__file__).parent / 'engine'

    #: Res d'això pot aparèixer en un import d'`engine/`.
    PROHIBITS = ('django', 'rest_framework')

    def _moduls(self) -> list[Path]:
        moduls = sorted(self.ENGINE.glob('*.py'))
        self.assertGreater(len(moduls), 1, 'No s\'ha trobat el codi de l\'engine.')
        return moduls

    def test_cap_import_de_django_ni_drf_dins_engine(self):
        import ast

        for path in self._moduls():
            with self.subTest(modul=path.name):
                arbre = ast.parse(path.read_text(), filename=str(path))
                for node in ast.walk(arbre):
                    if isinstance(node, ast.Import):
                        noms = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        # level > 0 és un import relatiu (from .geometry import …):
                        # intern a l'engine, que és exactament el que ha de fer.
                        noms = [node.module] if node.level == 0 and node.module else []
                    else:
                        continue

                    for nom in noms:
                        arrel = nom.split('.')[0]
                        self.assertNotIn(
                            arrel, self.PROHIBITS,
                            f'{path.name}:{node.lineno} importa "{nom}". '
                            f'engine/ és un paquet PUR: els adaptadors van fora.',
                        )
                        if arrel == 'fhort' and not nom.startswith('fhort.patterns.engine'):
                            self.fail(
                                f'{path.name}:{node.lineno} importa "{nom}": l\'engine '
                                f'no pot dependre de la resta de l\'app.'
                            )

    def test_lengine_simporta_sense_django_configurat(self):
        """El control que no es pot enganyar: importar-ho tot en un procés que no sap
        què és Django. Si algun mòdul arrossega l'ORM per una via indirecta, peta aquí."""
        import subprocess
        import sys

        moduls = [f'fhort.patterns.engine.{p.stem}' for p in self._moduls()
                  if p.stem != '__init__']
        codi = (
            'import importlib, sys\n'
            'assert "DJANGO_SETTINGS_MODULE" not in __import__("os").environ\n'
            + '\n'.join(f'importlib.import_module({m!r})' for m in moduls)
            + '\nassert "django" not in sys.modules, '
              '"engine ha carregat django per un import transitiu"\n'
        )
        entorn = {
            k: v for k, v in __import__('os').environ.items()
            if k != 'DJANGO_SETTINGS_MODULE'
        }
        proc = subprocess.run(
            [sys.executable, '-c', codi],
            cwd=str(Path(__file__).resolve().parents[2]),  # backend/
            env=entorn,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode, 0,
            f'L\'engine no s\'importa sense Django:\n{proc.stderr}',
        )


# ═════════════════════════════════════════════════════════════════════════════
# S7 — ESCALAT, EXPORT I GATE
# ═════════════════════════════════════════════════════════════════════════════

def _vora_recta_amb_corbes() -> PieceData:
    """Una vora GIR-corba-corba-corba-GIR, equiespaiada.

    L'AMELIA no serveix per provar el reflow: els seus punts d'ancoratge de POM són girs
    envoltats de girs (els ordres 8-20 del contorn de BACK són TOTS de gir), o sigui que
    entre ells no hi ha cap punt de corba que hagi de fluir. El reflow hi funciona i dona
    zero — que és correcte i no demostra res. Aquí, en canvi, les ràtios són conegudes a mà.
    """
    punts = (
        PointData(0.0, 0.0, PointKind.TURN),
        PointData(10.0, 0.0, PointKind.CURVE),
        PointData(20.0, 0.0, PointKind.CURVE),
        PointData(30.0, 0.0, PointKind.CURVE),
        PointData(40.0, 0.0, PointKind.TURN),
    )
    return PieceData(
        nom_block='RECTA',
        boundaries=(BoundaryData(role=LayerRole.CUT, layer='1', points=punts, closed=False),),
        notches=(NotchData(15.0, 0.0),),
    )


class OperacioAtomicaTest(unittest.TestCase):
    """Moure un punt no és moure un punt (v. docstring d'`operations`)."""

    def setUp(self):
        self.doc = PatternDocument(pieces=(_vora_recta_amb_corbes(),))

    def test_els_punts_de_corba_flueixen_per_ratio_de_longitud_darc(self):
        """El gir de l'esquerra es mou 10 mm; el de la dreta, gens. Els de corba es
        reparteixen el moviment segons què lluny són de cadascun."""
        res = move_points(self.doc, {PointRef('RECTA', 0, 0): (10.0, 0.0)})
        punts = res.document.piece('RECTA').boundaries[0].points

        # Ràtios d'arc sobre la geometria original: 0.25, 0.50, 0.75.
        self.assertAlmostEqual(punts[0].x, 10.0, places=6)   # el gir mogut
        self.assertAlmostEqual(punts[1].x, 10.0 + 7.5, places=6)
        self.assertAlmostEqual(punts[2].x, 20.0 + 5.0, places=6)
        self.assertAlmostEqual(punts[3].x, 30.0 + 2.5, places=6)
        self.assertAlmostEqual(punts[4].x, 40.0, places=6)   # el gir quiet

    def test_un_gir_quiet_ancora_el_reflow(self):
        """Si els girs no ancoressin, la vora sencera es desplaçaria rígida i la corba es
        deformaria: és la diferència entre graduar i arrossegar."""
        res = move_points(self.doc, {PointRef('RECTA', 0, 0): (10.0, 0.0)})
        self.assertEqual(res.informe.punts_moguts, 1)
        self.assertEqual(res.informe.punts_reflow, 3)

    def test_el_piquet_es_queda_sobre_la_vora(self):
        """Un piquet no té coordenades pròpies: té una posició SOBRE la vora."""
        res = move_points(self.doc, {PointRef('RECTA', 0, 0): (10.0, 0.0)})
        piquet = res.document.piece('RECTA').notches[0]

        # Seia a mig camí entre els punts 1 (10→17.5) i 2 (20→25). Hi continua seient.
        self.assertAlmostEqual(piquet.x, (17.5 + 25.0) / 2, places=6)
        self.assertAlmostEqual(piquet.y, 0.0, places=6)
        self.assertEqual(res.informe.piquets_reposicionats, 1)

    def test_el_document_original_no_es_toca_mai(self):
        """La geometria base persistida no es muta: l'operació construeix un document nou."""
        abans = self.doc.piece('RECTA').boundaries[0].points[0]
        res = move_points(self.doc, {PointRef('RECTA', 0, 0): (10.0, 0.0)})

        self.assertAlmostEqual(abans.x, 0.0)
        self.assertAlmostEqual(self.doc.piece('RECTA').boundaries[0].points[0].x, 0.0)
        self.assertAlmostEqual(res.document.piece('RECTA').boundaries[0].points[0].x, 10.0)
        self.assertIsNot(res.document, self.doc)

    def test_moure_un_punt_que_no_hi_es_es_un_avis_no_una_excepcio(self):
        res = move_points(self.doc, {PointRef('RECTA', 0, 99): (1.0, 0.0)})
        self.assertIn('punt_inexistent', [a.codi for a in res.informe.avisos])

    def test_el_pom_es_torna_a_LLEGIR_de_la_geometria_moguda(self):
        """El valor d'un POM no es recalcula amb una fórmula: es torna a mesurar."""
        spec = POMSpec('W', 'WIDTH', 'RECTA',
                       PointRef('RECTA', 0, 0), PointRef('RECTA', 0, 4))
        res = move_points(self.doc, {PointRef('RECTA', 0, 0): (-10.0, 0.0)}, poms=(spec,))

        # La vora feia 40 mm; el gir de l'esquerra se n'ha anat 10 mm cap enfora → 50 mm.
        self.assertAlmostEqual(res.informe.poms[0].valor_cm, 5.0, places=6)


class SewCosidorAMBTallTest(unittest.TestCase):
    """El camí has_sew, amb fixture sintètic: l'AMELIA no porta capa 14 (S0-B3)."""

    def _peca_amb_cosit(self) -> PieceData:
        tall = (
            PointData(0.0, 0.0, PointKind.TURN),
            PointData(50.0, 0.0, PointKind.CURVE),
            PointData(100.0, 0.0, PointKind.TURN),
        )
        # La línia de cosit, 10 mm endins: el marge de costura.
        cosit = (
            PointData(0.0, 10.0, PointKind.TURN),
            PointData(50.0, 10.0, PointKind.CURVE),
            PointData(100.0, 10.0, PointKind.TURN),
        )
        return PieceData(
            nom_block='P',
            boundaries=(
                BoundaryData(role=LayerRole.CUT, layer='1', points=tall, closed=False),
                BoundaryData(role=LayerRole.SEW, layer='14', points=cosit, closed=False),
            ),
            has_sew=True,
        )

    def test_el_cosit_segueix_el_tall_per_CORRESPONDENCIA_i_el_marge_es_conserva(self):
        """No per offset: un offset de polilínia crea vèrtexs a les cantonades (topologia
        nova, frontera §3.3) i, a més, no és el que fa el grading — la MATEIXA regla mou el
        punt de tall i el seu company del cosit."""
        doc = PatternDocument(pieces=(self._peca_amb_cosit(),))
        res = move_points(doc, {PointRef('P', 0, 2): (20.0, 0.0)})

        peca = res.document.piece('P')
        tall, cosit = peca.boundaries[0], peca.boundaries[1]

        # El gir del tall s'ha mogut, i el seu company del cosit també.
        self.assertAlmostEqual(tall.points[2].x, 120.0, places=6)
        self.assertAlmostEqual(cosit.points[2].x, 120.0, places=6)

        # I el marge de costura es conserva a tot arreu: és la invariant que ha d'aguantar.
        for pt, pc in zip(tall.points, cosit.points):
            self.assertAlmostEqual(pc.y - pt.y, 10.0, places=6)
            self.assertAlmostEqual(pc.x, pt.x, places=6)

        self.assertEqual(res.informe.punts_cosit_propagats, 2)


class EscalatTestBase(PatternsAPITestBase):
    """Un model amb grading APROVAT i un patró amb POMs ancorats: el terreny de S7."""

    #: Els deltes que el grading mana, en cm. Base S (delta 0 per definició).
    DELTES = {'S': 0.0, 'M': 1.0, 'L': 2.0, 'XL': 3.0, 'XXL': 4.0}

    def setUp(self):
        super().setUp()
        self.model.base_size_label = 'S'
        self.model.size_run_model = 'S·M·L·XL·XXL'
        self.model.save()

        self.fp = PatternFile.objects.get(
            pk=self._upload(AMELIA_DXF.read_bytes()).data['id'])
        self.back = self.fp.pieces.get(nom_block='BACK')
        self.girs = list(
            self.back.points.filter(mena='vertex', tipus='turn', boundary_index=0)
            .order_by('ordre'))

        self.pom = POMMaster.objects.create(codi_client='CHEST', nom_client='Chest width')
        # Un segon POM del catàleg que TÉ grading però que NO s'ancora enlloc.
        self.pom_orfe = POMMaster.objects.create(codi_client='WAIST', nom_client='Waist')

        from fhort.accounts.models import UserProfile
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tec', 'rol_nom': 'admin'})

        self.sf = SizeFitting.objects.create(
            model=self.model, numero=1, codi='SF-QA-1', tipus='Fit',
            estat='TallesGenerades', creat_per=self.profile)
        # aprovada=True i is_active=False A POSTA: són ORTOGONALS (S0-B7.1), i la versió
        # aprovada d'un model sovint NO és la que la UI serveix. Si el port confongués les
        # dues coses, aquest fixture el cantaria.
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, nom='QA aprovada', aprovada=True, is_active=False,
            creat_per=self.profile)

        for pom, base in ((self.pom, 50.0), (self.pom_orfe, 70.0)):
            for talla, delta in self.DELTES.items():
                GradedSpec.objects.create(
                    grading_version=self.gv, pom=pom, size_label=talla,
                    graded_value_cm=base + delta, increment_applied_cm=delta,
                    grading_type_applied='LINEAR', is_active=True,
                )

        # L'ancoratge: dos girs del contorn de tall de BACK.
        self.a, self.b = self.girs[0], self.girs[5]
        self.ancorat = PatternPOM.objects.create(
            pattern_piece=self.back, pom_master=self.pom,
            definicio_mesura={'mode': 'points', 'a': self.a.id, 'b': self.b.id},
            metode='recta',
        )
        self.ancorat.valor_mesurat_cm = round(
            math.hypot(self.b.x - self.a.x, self.b.y - self.a.y) / 10.0, 2)
        self.ancorat.save()

        self.base_mm = math.hypot(self.b.x - self.a.x, self.b.y - self.a.y)

    def _projectar(self):
        doc = DjangoGeometryStore().load_from(self.fp)
        snapshot = DjangoGradingSource().snapshot(self.gv.id)
        specs, _ = pom_specs(self.fp)
        return doc, snapshot, specs, project(doc, snapshot, specs, sew_specs(self.fp)[0])


class ProjeccioTest(EscalatTestBase):

    def test_el_pom_creix_EXACTAMENT_el_que_el_grading_mana(self):
        """La invariant de tot el sprint: mesura(talla) − mesura(base) == delta del spec."""
        doc, snapshot, specs, proj = self._projectar()
        previews = preview_per_talla(doc, proj, snapshot, specs)

        for sp in previews:
            pom = sp.poms[0]
            self.assertAlmostEqual(
                pom.valor_cm, (self.base_mm / 10.0) + self.DELTES[sp.talla], places=6,
                msg=f'talla {sp.talla}',
            )
            self.assertAlmostEqual(pom.desviament_cm, 0.0, places=9)
            self.assertTrue(pom.ok)

    def test_saplica_el_DELTA_i_no_el_valor_absolut(self):
        """`graded_value_cm` (50 cm) i el que el patró mesura (~66 cm) són magnituds
        DIFERENTS. Aplicar l'absolut estiraria el patró perquè digués el que diu la fitxa."""
        doc, snapshot, specs, proj = self._projectar()
        previews = preview_per_talla(doc, proj, snapshot, specs)

        base = next(sp for sp in previews if sp.es_base)
        self.assertAlmostEqual(base.poms[0].valor_cm, self.base_mm / 10.0, places=6)
        self.assertEqual(base.poms[0].valor_spec_cm, 50.0)   # el que la fitxa DECLARA
        self.assertNotAlmostEqual(base.poms[0].valor_cm, 50.0, places=1)

    def test_la_talla_base_no_es_mou(self):
        _, _, _, proj = self._projectar()
        for ref, (dx, dy) in proj.deltes_per_talla['S'].items():
            self.assertAlmostEqual(dx, 0.0, places=9)
            self.assertAlmostEqual(dy, 0.0, places=9)

    def test_una_regla_per_punt_mogut_i_la_regla_0_per_a_la_resta(self):
        _, _, _, proj = self._projectar()

        self.assertIn(0, proj.grade_table.regles)
        for delta in proj.grade_table.regles[0].deltes.values():
            self.assertEqual(delta, (0.0, 0.0))

        # Els punts de corba no porten regla: flueixen, i és el CAD qui els fa fluir.
        corbes = [
            p for peca in proj.document.pieces
            for b in peca.boundaries for p in b.points
            if p.kind is PointKind.CURVE
        ]
        self.assertTrue(corbes)
        self.assertTrue(all(p.grade_rule is None for p in corbes))

    def test_el_size_run_i_la_base_surten_del_MODEL_no_del_RUL_del_client(self):
        """El RUL d'AMELIA gradua XS-S-M-L-XL sobre M. El nostre gradua el que diu el model."""
        _, _, _, proj = self._projectar()
        self.assertEqual(proj.grade_table.talles, ('S', 'M', 'L', 'XL', 'XXL'))
        self.assertEqual(proj.grade_table.talla_base, 'S')


class OmissionsTest(EscalatTestBase):

    def test_un_pom_ancorat_sense_spec_es_diu_i_no_es_mou(self):
        orfe = POMMaster.objects.create(codi_client='SLEEVE', nom_client='Sleeve')
        PatternPOM.objects.create(
            pattern_piece=self.back, pom_master=orfe,
            definicio_mesura={'mode': 'points', 'a': self.girs[1].id, 'b': self.girs[6].id},
        )
        doc, snapshot, specs, proj = self._projectar()

        codis = [o.pom_code for o in proj.omissions if o.codi == 'pom_sense_spec']
        self.assertIn('SLEEVE', codis)

        # I no es mou a cap talla: el seu valor és el mateix a totes.
        previews = preview_per_talla(doc, proj, snapshot, specs)
        valors = {
            round(next(p.valor_cm for p in sp.poms if p.pom_code == 'SLEEVE'), 4)
            for sp in previews
        }
        self.assertEqual(len(valors), 1)

    def test_un_spec_sense_pom_ancorat_es_diu(self):
        _, _, _, proj = self._projectar()
        codis = [o.pom_code for o in proj.omissions if o.codi == 'spec_sense_pom']
        self.assertIn('WAIST', codis)

    def test_les_omissions_no_son_mai_silenci(self):
        _, _, _, proj = self._projectar()
        self.assertTrue(proj.omissions)
        for o in proj.omissions:
            self.assertTrue(o.missatge)


class GuardDelGradingTest(EscalatTestBase):

    def test_un_grading_NO_aprovat_no_escala(self):
        self.gv.aprovada = False
        self.gv.save()
        doc = DjangoGeometryStore().load_from(self.fp)
        snapshot = DjangoGradingSource().snapshot(self.gv.id)
        specs, _ = pom_specs(self.fp)

        with self.assertRaises(GradingNotApproved):
            project(doc, snapshot, specs)

    def test_dues_versions_aprovades_del_mateix_sizefitting_NO_peten_el_port(self):
        """C2 de S0-B7: cap constraint no impedeix que en coexisteixin dues. Un port que
        fes `get(aprovada=True)` petaria amb MultipleObjectsReturned **en exportar**."""
        segona = GradingVersion.objects.create(
            size_fitting=self.sf, nom='segona aprovada', aprovada=True, version_number=2)

        for gv in (self.gv, segona):
            snapshot = DjangoGradingSource().snapshot(gv.id)
            self.assertTrue(snapshot.approved)
            self.assertEqual(snapshot.grading_version_id, gv.id)

    def test_la_base_ve_DECLARADA_pel_model_no_deduida_del_delta_zero(self):
        """Un POM amb regla ZERO té delta 0 a TOTES les talles: deduir-ne la base seria
        agafar-ne una a l'atzar."""
        snapshot = DjangoGradingSource().snapshot(self.gv.id)
        self.assertEqual(snapshot.base_size_label, 'S')
        self.assertEqual(snapshot.size_run, ('S', 'M', 'L', 'XL', 'XXL'))

    def test_una_base_que_no_es_al_size_run_no_passa_en_silenci(self):
        self.model.base_size_label = 'XXS'
        self.model.save()
        doc = DjangoGeometryStore().load_from(self.fp)
        snapshot = DjangoGradingSource().snapshot(self.gv.id)

        with self.assertRaises(GradingContextError):
            project(doc, snapshot, pom_specs(self.fp)[0])


class SewPerTallaTest(EscalatTestBase):
    """La validació que un CAD no fa: les costures han de seguir casant a TOTES les talles."""

    def test_una_costura_es_revalida_a_cada_talla(self):
        front = self.fp.pieces.get(nom_block='FRONT')
        rel = SewRelation.objects.create(
            model=self.model, tipus='casat', diferencial_cm=0.0)
        rel.segments_a.add(self.back.segments.first())
        rel.segments_b.add(front.segments.first())

        doc, snapshot, specs, proj = self._projectar()
        previews = preview_per_talla(doc, proj, snapshot, specs, sew_specs(self.fp)[0])

        for sp in previews:
            self.assertEqual(len(sp.costures), 1, f'talla {sp.talla}')
            self.assertIsNotNone(sp.costures[0].check)
            # Casi o no casi, el veredicte hi ha de ser: el silenci no és una resposta.
            self.assertTrue(sp.costures[0].check.missatge)


class GateTest(EscalatTestBase):
    """El gate és una PRECONDICIÓ DURA: sense reconeixement no hi ha bytes."""

    def _export(self, **cos):
        request = self.factory.post(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/export/', cos, format='json')
        force_authenticate(request, user=self.user)
        return PatternFileViewSet.as_view({'post': 'export'})(request, pk=self.fp.id)

    def test_sense_reconeixement_no_hi_ha_bytes(self):
        resp = self._export(grading_version_id=self.gv.id)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(ExportAcknowledgement.objects.count(), 0)

    def test_un_acknowledged_fals_tampoc(self):
        resp = self._export(grading_version_id=self.gv.id, acknowledged=False)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(ExportAcknowledgement.objects.count(), 0)

    def test_amb_reconeixement_surten_els_bytes_i_queda_el_registre(self):
        resp = self._export(grading_version_id=self.gv.id, acknowledged=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b'  0\nSECTION'))
        self.assertIn('attachment', resp['Content-Disposition'])

        ack = ExportAcknowledgement.objects.get()
        self.assertEqual(ack.pattern_file_id, self.fp.id)
        self.assertEqual(ack.versio_patro, self.fp.versio)
        self.assertEqual(ack.grading_version_id, self.gv.id)
        self.assertEqual(ack.destination_profile, 'polypattern')
        # El text que se li va ensenyar, literal: si el text canvia, això ha de continuar
        # dient què va acceptar aquesta persona.
        self.assertIn('verificar', ack.texts_shown)

    def test_no_es_pot_exportar_amb_un_grading_no_aprovat(self):
        self.gv.aprovada = False
        self.gv.save()
        resp = self._export(grading_version_id=self.gv.id, acknowledged=True)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(ExportAcknowledgement.objects.count(), 0)

    def test_un_perfil_sense_fitxer_real_de_referencia_es_rebutja(self):
        """Escriure'n l'empremta sense haver vist mai un fitxer d'aquell CAD seria
        inventar-se-la, i un round-trip verd contra una empremta inventada dona confiança
        falsa."""
        resp = self._export(grading_version_id=self.gv.id, acknowledged=True,
                            destination_profile='gerber')
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(ExportAcknowledgement.objects.count(), 0)

    def test_la_previsualitzacio_no_deixa_cap_registre(self):
        """Mirar no és reconèixer."""
        request = self.factory.post(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/export-preview/',
            {'grading_version_id': self.gv.id}, format='json')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'post': 'export_preview'})(request, pk=self.fp.id)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['autovalidacio']['ok'])
        self.assertEqual(len(resp.data['talles']), 5)
        self.assertEqual(ExportAcknowledgement.objects.count(), 0)

    def test_nomes_sofereixen_versions_APROVADES(self):
        GradingVersion.objects.create(
            size_fitting=self.sf, nom='esborrany', aprovada=False, is_active=True)

        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/grading-versions/')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view(
            {'get': 'grading_versions'})(request, pk=self.fp.id)

        self.assertEqual([v['id'] for v in resp.data], [self.gv.id])


class AutovalidacioTest(EscalatTestBase):
    """La porta: si el fitxer emès no es torna a llegir igual, NO surt cap byte."""

    def test_lexport_normal_passa_lautovalidacio(self):
        resultat = build_export(self.fp, self.gv.id, 'polypattern')
        self.assertTrue(resultat.autovalidacio.ok, resultat.autovalidacio.diferencies)
        self.assertGreater(resultat.autovalidacio.punts_comparats, 0)
        self.assertEqual(
            resultat.autovalidacio.cens_volta_1, resultat.autovalidacio.cens_volta_2)

    def test_un_writer_espatllat_BLOQUEJA_lexportacio(self):
        """Es trenca el writer a posta: si es menja els TEXT de regla, el fitxer surt sense
        grading. La porta ho ha de veure i no deixar sortir res."""
        original = AAMAWriter._write_rule_texts

        def _sabotatge(self, block, piece, factor, height):
            return None   # el fitxer surt sense cap número de regla

        with mock.patch.object(AAMAWriter, '_write_rule_texts', _sabotatge):
            with self.assertRaises(ExportBlocked) as ctx:
                build_export(self.fp, self.gv.id, 'polypattern')

        self.assertIn('diferencies', ctx.exception.detall)
        self.assertTrue(ctx.exception.detall['diferencies'])
        self.assertEqual(AAMAWriter._write_rule_texts, original)

    def test_una_geometria_moguda_a_posta_BLOQUEJA_lexportacio(self):
        """I si el que es corromp és un punt, també: 5 mm de desplaçament silenciós són una
        peça mal tallada."""
        original = AAMAWriter._write_piece

        def _sabotatge(self, block, piece, cfg, factor, height):
            moguda = replace(piece, boundaries=tuple(
                replace(b, points=tuple(
                    replace(p, x=p.x + 5.0) if i == 0 else p
                    for i, p in enumerate(b.points)
                ))
                for b in piece.boundaries
            ))
            return original(self, block, moguda, cfg, factor, height)

        with mock.patch.object(AAMAWriter, '_write_piece', _sabotatge):
            with self.assertRaises(ExportBlocked) as ctx:
                build_export(self.fp, self.gv.id, 'polypattern')

        diferencies = ' '.join(ctx.exception.detall['diferencies'])
        self.assertIn('point_moved', diferencies)

    def test_la_capa_FTT_POM_del_fitxer_emes_es_rellegeix_com_a_taula(self):
        """El guionitzat de S8: el DXF que exportem s'ha de poder reimportar i la seva capa
        POM s'ha de llegir com una taula idèntica als PatternPOM de la BD."""
        resultat = build_export(self.fp, self.gv.id, 'polypattern')
        tornat = AAMAReader().read(resultat.dxf)

        poms = {p.pom_code: p for peca in tornat.pieces for p in peca.poms}
        self.assertIn('CHEST', poms)
        self.assertAlmostEqual(
            poms['CHEST'].valor_mesurat_mm, self.base_mm, places=2)

    def test_el_RUL_emes_porta_les_regles_poblades(self):
        resultat = build_export(self.fp, self.gv.id, 'polypattern')
        taula = RULReader().read(resultat.rul)

        self.assertEqual(taula.talles, ('S', 'M', 'L', 'XL', 'XXL'))
        self.assertEqual(taula.talla_base, 'S')
        self.assertIn(0, taula.regles)
        # Hi ha d'haver com a mínim una regla que mogui alguna cosa de debò.
        self.assertTrue(any(
            any(d != (0.0, 0.0) for d in regla.deltes.values())
            for num, regla in taula.regles.items() if num != 0
        ))


# ═════════════════════════════════════════════════════════════════════════════
# TALLER DE PATRÓ · W1 — SEGMENTS DECLARATS
# ═════════════════════════════════════════════════════════════════════════════

class TramEntrePuntsTest(unittest.TestCase):
    """La primitiva del segment declarat, contra el TATE real.

    El TATE és el patró amb què s'ha fet el QA, i porta el que l'AMELIA no té: capa 14. Els
    trams de veritat es deriven de la línia de COSIT, i és sobre aquella vora que el
    patronista declara.
    """

    @classmethod
    def setUpClass(cls):
        cls.md5 = hashlib.md5(TATE_DXF.read_bytes()).hexdigest()
        cls.doc = AAMAReader().read(TATE_DXF.read_bytes())
        cls.piece = cls.doc.piece('TATE_FRONT')
        # La vora de COSIT: la que de debò es cus, i de la qual es deriven els trams.
        cls.vora = next(i for i, b in enumerate(cls.piece.boundaries)
                        if b.role is LayerRole.SEW)
        cls.boundary = cls.piece.boundaries[cls.vora]
        cls.total_mm = longitud_vora(cls.boundary)

    def test_el_material_no_ha_canviat(self):
        self.assertEqual(self.md5, TATE_DXF_MD5)
        self.assertTrue(self.boundary.closed)
        self.assertAlmostEqual(self.total_mm / 10.0, 183.1, places=1)

    def test_els_dos_arcs_sumen_la_vora_sencera(self):
        """La prova que el tram és una REFERÈNCIA a la vora i no geometria nova: el que hi
        ha entre dos punts, més el que hi ha per l'altre costat, és la vora i prou."""
        curt = tram_entre_punts(self.boundary, self.vora, 3, 33)
        llarg = tram_entre_punts(self.boundary, self.vora, 3, 33, arc_llarg=True)

        self.assertAlmostEqual(curt.longitud_mm + llarg.longitud_mm, self.total_mm, places=6)
        self.assertLess(curt.longitud_mm, llarg.longitud_mm)

    def test_larc_llarg_dona_la_volta_per_lorigen(self):
        """Un tram que travessa el punt on la polilínia tanca es guarda amb t_fi < t_inici, i
        la seva longitud NO és una resta."""
        llarg = tram_entre_punts(self.boundary, self.vora, 3, 33, arc_llarg=True)

        self.assertLess(llarg.t_fi, llarg.t_inici)   # dona la volta
        self.assertAlmostEqual(
            fraccio_tram(llarg.t_inici, llarg.t_fi) * self.total_mm,
            llarg.longitud_mm, places=6)
        # Una resta pelada donaria negatiu: és el bug que fraccio_tram evita.
        self.assertLess(llarg.t_fi - llarg.t_inici, 0)

    def test_punts_a_mig_tram_auto(self):
        """Els extrems NO han de ser punts de gir: aquest és tot el sentit de declarar.

        Es tria un punt enmig del primer tram derivat i un altre enmig del segon: cap dels
        dos és frontera de res per al CAD, i tots dos ho són per al patronista.
        """
        girs = [i for i, p in enumerate(self.boundary.points) if p.kind is PointKind.TURN]
        a, b = girs[0] + 3, girs[1] + 5
        self.assertIsNot(self.boundary.points[a].kind, PointKind.TURN)
        self.assertIsNot(self.boundary.points[b].kind, PointKind.TURN)

        tram = tram_entre_punts(self.boundary, self.vora, a, b)

        self.assertGreater(tram.longitud_mm, 0)
        self.assertEqual(tram.index_inici, a)
        self.assertEqual(tram.index_fi, b)

    def test_el_tram_segueix_la_vora_no_la_recta(self):
        """La longitud és el RECORREGUT, no la distància entre els extrems. En una corba
        (una sisa) les dues xifres no s'assemblen, i confondre-les seria mesurar una corda."""
        girs = [i for i, p in enumerate(self.boundary.points) if p.kind is PointKind.TURN]
        a, b = girs[0], girs[1]
        pa, pb = self.boundary.points[a], self.boundary.points[b]
        recta = math.hypot(pb.x - pa.x, pb.y - pa.y)

        tram = tram_entre_punts(self.boundary, self.vora, a, b)

        self.assertGreater(tram.longitud_mm, recta)

    def test_un_tram_declarat_pot_coincidir_amb_un_dauto(self):
        """Declarar de gir a gir ha de donar EXACTAMENT el tram derivat. Si no, les dues
        vies no parlarien de la mateixa vora."""
        auto = segmentar_peca(self.piece)[0]

        tram = tram_entre_punts(self.boundary, self.vora, auto.index_inici, auto.index_fi)

        self.assertAlmostEqual(tram.longitud_mm, auto.longitud_mm, places=6)
        self.assertAlmostEqual(tram.t_inici, auto.t_inici, places=9)

    def test_el_mateix_punt_dues_vegades_no_es_cap_tram(self):
        with self.assertRaises(SegmentError):
            tram_entre_punts(self.boundary, self.vora, 7, 7)

    def test_un_punt_fora_de_la_vora(self):
        with self.assertRaises(SegmentError):
            tram_entre_punts(self.boundary, self.vora, 0, 99999)

    def test_una_vora_oberta_no_te_arc_llarg(self):
        """No hi ha dos camins entre dos punts d'una línia: demanar-hi el llarg és una
        contradicció, i es diu, en comptes de tornar l'únic que hi ha fent el distret."""
        interna = next(b for b in self.piece.boundaries if not b.closed)

        with self.assertRaises(SegmentError):
            tram_entre_punts(interna, 1, 0, 1, arc_llarg=True)

        # Però el tram normal sí que existeix.
        tram = tram_entre_punts(interna, 1, 0, 1)
        self.assertGreater(tram.longitud_mm, 0)


class CoberturaVoraTest(unittest.TestCase):
    """La validació que només es veu mirant la vora sencera.

    Xifres rodones a posta: aquí es prova la REGLA. Que la regla parla de patrons de debò ja
    ho prova `TramEntrePuntsTest` amb el TATE.
    """

    def test_dues_costures_que_reclamen_el_mateix_tram(self):
        """SOLAPAMENT: cadascuna casa perfectament; juntes, cusen dues vegades la mateixa
        tela. És el defecte que els trams gir→gir feien impossible i els declarats permeten."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.0, t_fi=0.5, nom='lateral'),
            TramCosit(sew_id=2, segment_id=11, t_inici=0.4, t_fi=0.6, nom='sisa'),
        ]

        avisos = validar_cobertura(vora=0, longitud_vora_mm=1000.0, trams=trams)

        solap = [a for a in avisos if a.mena == MENA_SOLAPAMENT]
        self.assertEqual(len(solap), 1)
        # 0.4→0.5 d'una vora de 100 cm = 10 cm de tela reclamada dues vegades.
        self.assertAlmostEqual(solap[0].solapament_cm, 10.0, places=2)
        self.assertEqual(solap[0].sews, (1, 2))
        self.assertIn('10.0 cm', solap[0].missatge)

    def test_les_costures_sumen_mes_tela_de_la_que_hi_ha(self):
        """EXCÉS: la peça no té tanta vora. Amb xifres, no amb un 'revisa-ho'."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.0, t_fi=0.7),
            TramCosit(sew_id=2, segment_id=11, t_inici=0.6, t_fi=1.0),
        ]

        avisos = validar_cobertura(vora=0, longitud_vora_mm=1000.0, trams=trams)

        exces = [a for a in avisos if a.mena == MENA_EXCES]
        self.assertEqual(len(exces), 1)
        self.assertAlmostEqual(exces[0].longitud_vora_cm, 100.0, places=2)
        self.assertAlmostEqual(exces[0].suma_cosida_cm, 110.0, places=2)
        self.assertAlmostEqual(exces[0].exces_cm, 10.0, places=2)

    def test_una_vora_ben_coberta_no_diu_res(self):
        """Trams consecutius que no es trepitgen i hi caben: silenci. Un validador que
        avisés igualment ensenyaria a ignorar-lo."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.0, t_fi=0.5),
            TramCosit(sew_id=2, segment_id=11, t_inici=0.5, t_fi=1.0),
        ]

        self.assertEqual(validar_cobertura(0, 1000.0, trams), [])

    def test_el_solapament_veu_els_trams_que_donen_la_volta(self):
        """Un tram que passa per l'origen (t_fi < t_inici) es trepitja amb un que comença a
        zero. Si la comparació fos una resta, no ho veuria."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.9, t_fi=0.1),   # dona la volta
            TramCosit(sew_id=2, segment_id=11, t_inici=0.0, t_fi=0.05),
        ]

        avisos = validar_cobertura(vora=0, longitud_vora_mm=1000.0, trams=trams)

        solap = [a for a in avisos if a.mena == MENA_SOLAPAMENT]
        self.assertEqual(len(solap), 1)
        self.assertAlmostEqual(solap[0].solapament_cm, 5.0, places=2)

    def test_una_costura_que_es_trepitja_a_ella_mateixa(self):
        """Els dos trams del MATEIX costat que se superposen: el costat compta la tela dues
        vegades i la costura sembla més llarga del que és."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.0, t_fi=0.5),
            TramCosit(sew_id=1, segment_id=11, t_inici=0.3, t_fi=0.6),
        ]

        avisos = validar_cobertura(vora=0, longitud_vora_mm=1000.0, trams=trams)

        solap = [a for a in avisos if a.mena == MENA_SOLAPAMENT]
        self.assertEqual(len(solap), 1)
        self.assertIn('es trepitja a ella mateixa', solap[0].missatge)

    def test_una_vora_degenerada_no_genera_soroll(self):
        self.assertEqual(validar_cobertura(0, 0.0, [TramCosit(1, 10, 0.0, 1.0)]), [])


class PincaTest(unittest.TestCase):
    """La pinça, contra el TATE real (Taller de patró · W4b).

    El cas que va obligar a construir això és aquest, i és per això que el test és aquest i
    no un de xifres rodones: al TATE, la costura lateral uneix un tram del davanter que fa
    **32.13 cm** de contorn amb un tram de l'esquena que en fa **29.80**. Es diferencien en
    2.33 cm i el patró està BÉ: al mig del tram del davanter hi ha una pinça, i la tela dels
    seus dos costats no arriba mai a la costura.

    Sense el descompte, el motor deia "no casa per 2.3 cm" d'un patró correcte —que és la
    manera més segura d'ensenyar-li al patronista que el vermell no vol dir res.
    """

    #: Els vèrtexs del TATE_FRONT (vora de cosit) que aquest cas fa servir. Surten de la
    #: geometria, no d'un catàleg: 68→72 és el tram lateral que el patronista va declarar, i
    #: 69→70→71 és la pinça que hi ha a dins (tres punts de GIR consecutius que fan una V).
    TRAM_INICI, TRAM_FI = 68, 72
    PINCA_A, PINCA_VERTEX, PINCA_B = 69, 70, 71

    @classmethod
    def setUpClass(cls):
        doc = AAMAReader().read(TATE_DXF.read_bytes())

        davant = doc.piece('TATE_FRONT')
        cls.i_davant = next(i for i, b in enumerate(davant.boundaries)
                            if b.role is LayerRole.SEW)
        cls.davant = davant.boundaries[cls.i_davant]

        esquena = doc.piece('TATE_BACK')
        i_esquena = next(i for i, b in enumerate(esquena.boundaries)
                         if b.role is LayerRole.SEW)
        cls.esquena = esquena.boundaries[i_esquena]

        # El tram lateral de cada peça, tal com es va declarar al taller.
        cls.tram_davant = tram_entre_punts(
            cls.davant, cls.i_davant, cls.TRAM_INICI, cls.TRAM_FI)
        cls.tram_esquena = tram_entre_punts(cls.esquena, i_esquena, 165, 167)

        # Els dos costats de la pinça, cadascun un tram declarat.
        cls.costat_a = tram_entre_punts(
            cls.davant, cls.i_davant, cls.PINCA_A, cls.PINCA_VERTEX)
        cls.costat_b = tram_entre_punts(
            cls.davant, cls.i_davant, cls.PINCA_VERTEX, cls.PINCA_B)

    def _pinca(self, nom='Pinça 1', sew_id=99):
        """Els dos costats de la pinça del TATE, com el motor els vol."""
        return [
            CostatPinca(sew_id=sew_id, segment_id=n, nom=nom,
                        t_inici=tr.t_inici, t_fi=tr.t_fi,
                        longitud_cm=tr.longitud_mm / 10.0)
            for n, tr in ((1, self.costat_a), (2, self.costat_b))
        ]

    # ── El material: les xifres del cas real ────────────────────────────────
    def test_les_xifres_del_tate_son_les_del_cas(self):
        """Si el fitxer canviés, tot el que ve després deixaria de provar el que diu provar."""
        self.assertAlmostEqual(self.tram_davant.longitud_mm / 10, 32.13, places=2)
        self.assertAlmostEqual(self.tram_esquena.longitud_mm / 10, 29.80, places=2)
        # El no-casa exacte: 2.33 cm.
        self.assertAlmostEqual(
            (self.tram_davant.longitud_mm - self.tram_esquena.longitud_mm) / 10,
            2.33, places=2)

    def test_els_dos_costats_de_la_pinca_sumen_el_que_falla(self):
        """La hipòtesi sencera del sprint, en una línia: el que sobra al davanter ÉS la pinça.

        2.34 (costats) vs 2.33 (no-casa): 0.1 mm de diferència, que és la boca de la pinça
        contra la corda dels seus costats. Per sota de la tolerància, i per això casa."""
        suma = (self.costat_a.longitud_mm + self.costat_b.longitud_mm) / 10
        self.assertAlmostEqual(suma, 2.34, places=2)

    def test_la_pinca_es_dins_del_tram_lateral(self):
        """Si no hi fos a dins, no seria una pinça d'aquesta costura i no s'hi descomptaria."""
        for costat in (self.costat_a, self.costat_b):
            self.assertTrue(conte(
                self.tram_davant.t_inici, self.tram_davant.t_fi,
                costat.t_inici, costat.t_fi))

    # ── La regla ────────────────────────────────────────────────────────────
    def test_sense_descompte_el_tate_correcte_surt_vermell(self):
        """El bug que això arregla, escrit com a test: un patró bo, denunciat."""
        c = validar(self.tram_davant.longitud_mm, self.tram_esquena.longitud_mm, 'casat')

        self.assertFalse(c.casa)
        self.assertAlmostEqual(c.desviament_cm, 2.33, places=2)

    def test_amb_la_pinca_declarada_la_costura_lateral_del_tate_CASA(self):
        """El cas real, sencer. I l'aritmètica sencera al missatge: 32.1 − 2.3 = 29.8."""
        tram = TramCosit(
            sew_id=1, segment_id=10, nom='Lateral',
            t_inici=self.tram_davant.t_inici, t_fi=self.tram_davant.t_fi)
        descomptes = descomptar_pinces([tram], self._pinca())

        c = validar(
            self.tram_davant.longitud_mm, self.tram_esquena.longitud_mm, 'casat',
            descomptes_a=descomptes,
        )

        self.assertTrue(c.casa)
        # El BRUT es conserva: la vora continua fent 32.13, i això no és un secret.
        self.assertAlmostEqual(c.brut_a_cm, 32.13, places=2)
        self.assertAlmostEqual(c.longitud_a_cm, 29.79, places=2)   # el NET, que és el que es cus
        self.assertLess(c.desviament_cm, 0.1)
        self.assertEqual(len(c.descomptes_a), 1)
        self.assertEqual(c.descomptes_a[0].nom, 'Pinça 1')
        # L'operació, no el resultat: qui la llegeixi l'ha de poder anar a comprovar.
        self.assertIn('32.1 − 2.3 (Pinça 1) = 29.8', c.missatge)

    def test_una_pinca_es_reporta_sencera_i_no_pas_per_costats(self):
        """El patronista reconeix LA PINÇA, no les seves meitats: un descompte, no dos."""
        tram = TramCosit(1, 10, self.tram_davant.t_inici, self.tram_davant.t_fi)

        descomptes = descomptar_pinces([tram], self._pinca())

        self.assertEqual(len(descomptes), 1)
        self.assertAlmostEqual(descomptes[0].cm, 2.34, places=2)

    def test_una_pinca_de_fora_del_tram_no_es_descompta(self):
        """Descomptar una pinça que la costura no conté seria inventar-se tela.

        El tram és l'ALTRE costat de la vora; la pinça continua sent on era."""
        altre = tram_entre_punts(self.davant, self.i_davant, self.TRAM_INICI, self.TRAM_FI,
                                 arc_llarg=True)
        tram = TramCosit(1, 10, altre.t_inici, altre.t_fi)

        self.assertEqual(descomptar_pinces([tram], self._pinca()), [])

    def test_una_pinca_a_mitges_no_es_descompta(self):
        """Conteniment ESTRICTE: mig costat dins no és mitja pinça, és una declaració
        dolenta. Val més una costura que no casa i es pot investigar que una que casa perquè
        el motor s'ha inventat el que hi cabia."""
        # Un tram que talla la pinça pel mig: comença al vèrtex i acaba al final del tram.
        mig = tram_entre_punts(self.davant, self.i_davant, self.PINCA_VERTEX, self.TRAM_FI)
        tram = TramCosit(1, 10, mig.t_inici, mig.t_fi)

        descomptes = descomptar_pinces([tram], self._pinca())

        # Només hi cau el costat B (vèrtex→final); el A queda fora i la pinça no és sencera.
        self.assertEqual(len(descomptes), 1)
        self.assertAlmostEqual(descomptes[0].cm, self.costat_b.longitud_mm / 10, places=3)

    # ── La cobertura ────────────────────────────────────────────────────────
    def test_la_pinca_continguda_no_es_un_conflicte_de_cobertura(self):
        """Sense l'excepció, declarar la pinça del TATE encenia DOS avisos falsos —solapament
        i excés— sobre una vora que està perfectament bé. La costura ja no cus aquella tela:
        `validar` l'hi ha descomptada, i comptar-la aquí seria comptar-la dues vegades."""
        pinca = self._pinca()
        trams = [
            TramCosit(sew_id=1, segment_id=10, nom='Lateral',
                      t_inici=self.tram_davant.t_inici, t_fi=self.tram_davant.t_fi),
            *[TramCosit(sew_id=c.sew_id, segment_id=c.segment_id, nom=c.nom,
                        t_inici=c.t_inici, t_fi=c.t_fi, es_pinca=True) for c in pinca],
        ]

        avisos = validar_cobertura(
            vora=self.i_davant, longitud_vora_mm=longitud_vora(self.davant), trams=trams)

        self.assertEqual(avisos, [])

    def test_una_pinca_que_no_cus_ningu_SI_que_compta(self):
        """L'excepció és estreta: val per a la pinça que una costura conté, no per a
        qualsevol tram etiquetat de pinça. Una pinça declarada al mig de res reclama tela de
        debò, i si no hi cap s'ha de dir."""
        trams = [
            TramCosit(sew_id=1, segment_id=10, t_inici=0.0, t_fi=0.95),
            TramCosit(sew_id=2, segment_id=11, t_inici=0.96, t_fi=0.99, es_pinca=True),
            TramCosit(sew_id=2, segment_id=12, t_inici=0.99, t_fi=1.0, es_pinca=True),
        ]

        avisos = validar_cobertura(vora=0, longitud_vora_mm=1000.0, trams=trams)

        # 0.95 + 0.03 + 0.01 = 0.99 de la vora: hi cap, i no es diu res. Però els costats de
        # pinça HAN comptat — el que es prova és que no s'han neutralitzat.
        self.assertEqual(avisos, [])
        trams_massa = [*trams, TramCosit(sew_id=3, segment_id=13, t_inici=0.0, t_fi=0.05)]
        exces = [a for a in validar_cobertura(0, 1000.0, trams_massa)
                 if a.mena == MENA_EXCES]
        self.assertEqual(len(exces), 1)
        # Si els costats de pinça no comptessin, la suma seria 1.00 i no hi hauria excés.
        self.assertAlmostEqual(exces[0].suma_cosida_cm, 104.0, places=2)


class NaturalsAPITest(PatternsAPITestBase):
    """Els naturals arriben amb la geometria, amb el TATE real pujat per l'API."""

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])

    def _peces(self):
        return {p['nom_block']: p for p in PatternGeometrySerializer(self.fp).data['pieces']}

    def test_el_tate_front_surt_amb_vuit_costures_i_no_amb_vint_i_cinc(self):
        """El cas del sprint, end-to-end: el CAD en marca 25, l'ofici en llegeix 8."""
        front = self._peces()['TATE_FRONT']
        auto = [s for s in front['segments'] if s['origen'] == 'auto']
        self.assertEqual(len(auto), 25)
        self.assertEqual(len(front['naturals']), 8)

    def test_els_naturals_no_substitueixen_els_auto(self):
        """Vista derivada: els AUTO segueixen sencers al mateix payload, perquè el gest
        manual de precisió i l'aritmètica els necessiten."""
        for nom, p in self._peces().items():
            with self.subTest(peca=nom):
                auto = [s for s in p['segments'] if s['origen'] == 'auto']
                if not auto:
                    continue
                self.assertLessEqual(len(p['naturals']), len(auto))

    def test_un_natural_del_tate_es_la_costura_que_l_huma_va_declarar(self):
        """La validació que no es pot arreglar amb un número: la capa retroba SOLA la
        lateral que el patronista havia marcat a mà a W4b (32,13 cm)."""
        front = self._peces()['TATE_FRONT']
        llargs = [s['longitud_cm'] for s in front['naturals']]
        self.assertIn(32.13, llargs)
        esquena = self._peces()['TATE_BACK']
        self.assertIn(29.8, [s['longitud_cm'] for s in esquena['naturals']])

    def test_els_piquets_viatgen_dins_del_natural(self):
        """No tallen, però hi són: A2 els llegeix per inferir frunzit."""
        front = self._peces()['TATE_FRONT']
        lateral = next(s for s in front['naturals'] if s['longitud_cm'] == 32.13)
        self.assertEqual(len(lateral['piquets']), 2)
        # I la fusió diu de quins girs surt.
        self.assertTrue(lateral['girs_fusionats'])


class SegmentDeclaratAPITest(PatternsAPITestBase):
    """CRUD del tram declarat, amb el TATE real pujat per l'API."""

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])
        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')
        # La vora de COSIT: la que es cus i de la qual pengen els trams derivats.
        self.vora = self.front.segments.filter(origen=PatternSegment.ORIGEN_AUTO).first().vora
        self.punts = list(
            self.front.points.filter(mena='vertex', boundary_index=self.vora).order_by('ordre'))
        # L'altre costat de les costures viu a una peça DIFERENT, com al món: una costura
        # uneix dues peces. Fer servir un tram de la mateixa vora com a costat B faria que la
        # costura es trepitgés a ella mateixa —cosa que el validador detecta, correctament, i
        # que taparia el solapament ENTRE costures que aquests tests volen provar.
        self.back = self.fp.pieces.get(nom_block='TATE_BACK')
        trams_back = list(
            self.back.segments.filter(origen=PatternSegment.ORIGEN_AUTO)[:2])
        self.tram_back, self.tram_back_2 = trams_back[0], trams_back[1]

    def _declara(self, a, b, nom='costura lateral', **extra):
        dades = {'point_a': a.id, 'point_b': b.id, 'nom': nom}
        dades.update(extra)
        request = self.factory.post(
            '/api/v1/patterns/pattern-segments/', dades, format='json')
        force_authenticate(request, user=self.user)
        return PatternSegmentViewSet.as_view({'post': 'create'})(request)

    def _esborra(self, seg_id):
        request = self.factory.delete(f'/api/v1/patterns/pattern-segments/{seg_id}/')
        force_authenticate(request, user=self.user)
        return PatternSegmentViewSet.as_view({'delete': 'destroy'})(request, pk=seg_id)

    def test_els_derivats_no_els_ha_declarat_ningu(self):
        """L'import deixa les dues lectures derivades ('auto' i 'natural') i cap declarat:
        un tram declarat és una afirmació d'algú, i en importar encara no n'hi ha cap."""
        self.assertGreater(
            self.front.segments.filter(origen=PatternSegment.ORIGEN_AUTO).count(), 0)
        self.assertGreater(
            self.front.segments.filter(origen=PatternSegment.ORIGEN_NATURAL).count(), 0)
        self.assertFalse(
            self.front.segments.filter(origen=PatternSegment.ORIGEN_DECLARAT).exists())

    def test_declarar_un_tram_entre_dos_punts(self):
        resp = self._declara(self.punts[3], self.punts[33])

        self.assertEqual(resp.status_code, 201, resp.data)
        seg = PatternSegment.objects.get(pk=resp.data['id'])
        self.assertEqual(seg.origen, PatternSegment.ORIGEN_DECLARAT)
        self.assertEqual(seg.nom, 'costura lateral')
        self.assertEqual(seg.vora, self.vora)
        self.assertGreater(resp.data['longitud_cm'], 0)
        self.assertFalse(resp.data['en_us'])

    def test_larc_llarg_es_mes_llarg(self):
        curt = self._declara(self.punts[3], self.punts[33], nom='curt')
        llarg = self._declara(self.punts[3], self.punts[33], nom='llarg', arc_llarg=True)

        self.assertEqual(llarg.status_code, 201, llarg.data)
        self.assertGreater(llarg.data['longitud_cm'], curt.data['longitud_cm'])

    def test_el_client_no_pot_enviar_la_geometria(self):
        """Les t no s'accepten: arriben dos punts i el servidor resol. Si el client pogués
        dictar-les, un tram deixaria de ser una referència a la vora."""
        resp = self._declara(self.punts[3], self.punts[33], t_inici=0.0, t_fi=1.0)

        seg = PatternSegment.objects.get(pk=resp.data['id'])
        self.assertNotEqual((seg.t_inici, seg.t_fi), (0.0, 1.0))

    def test_dos_punts_de_peces_diferents(self):
        altra = self.fp.pieces.get(nom_block='TATE_BACK')
        punt_altra = altra.points.filter(mena='vertex').first()

        resp = self._declara(self.punts[0], punt_altra)

        self.assertEqual(resp.status_code, 400)

    def test_un_piquet_no_pot_ser_extrem(self):
        piquet = self.front.points.filter(mena='notch').first()
        if piquet is None:
            self.skipTest('El TATE_FRONT no porta piquets.')

        resp = self._declara(self.punts[0], piquet)

        self.assertEqual(resp.status_code, 400)

    def test_esborrar_un_tram_que_ningu_no_cus(self):
        seg_id = self._declara(self.punts[3], self.punts[33]).data['id']

        resp = self._esborra(seg_id)

        self.assertEqual(resp.status_code, 204)
        self.assertFalse(PatternSegment.objects.filter(pk=seg_id).exists())

    def test_no_sesborra_un_tram_que_una_costura_fa_servir(self):
        """PROTECT a mà (el M2M no en té): esborrar-lo deixaria la costura coixa en silenci."""
        seg_id = self._declara(self.punts[3], self.punts[33]).data['id']
        rel = SewRelation.objects.create(model=self.model, tipus='casat')
        rel.segments_a.add(seg_id)
        rel.segments_b.add(self.tram_back)

        resp = self._esborra(seg_id)

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['sew_relations'], [rel.id])
        self.assertTrue(PatternSegment.objects.filter(pk=seg_id).exists())

    # ── ESBORRAT EN BLOC (QA-TALLER E · T3) ─────────────────────────────────

    def _esborra_bloc(self, ids):
        request = self.factory.post(
            '/api/v1/patterns/pattern-segments/bulk-delete/', {'ids': ids}, format='json')
        force_authenticate(request, user=self.user)
        return PatternSegmentViewSet.as_view({'post': 'bulk_delete'})(request)

    def test_el_bloc_esborra_els_trams_que_ningu_no_cus(self):
        a = self._declara(self.punts[3], self.punts[33]).data['id']
        b = self._declara(self.punts[40], self.punts[60]).data['id']

        resp = self._esborra_bloc([a, b])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [a, b])
        self.assertEqual(resp.data['retinguts'], [])
        self.assertFalse(PatternSegment.objects.filter(pk__in=[a, b]).exists())

    def test_un_tram_retingut_no_atura_lesborrat_dels_altres(self):
        """El cor de T3: qui n'ha demanat tres no ha demanat «tot o res», n'ha demanat tres.

        Si el bloc fos una transacció sola, una sola costura faria caure la feina sencera i
        la pantalla no sabria dir QUÈ ha quedat viu. L'atomicitat és per ítem, i el que es
        queda es diu id per id.
        """
        lliure = self._declara(self.punts[3], self.punts[33]).data['id']
        cosit = self._declara(self.punts[40], self.punts[60]).data['id']
        rel = SewRelation.objects.create(model=self.model, tipus='casat')
        rel.segments_a.add(cosit)
        rel.segments_b.add(self.tram_back)

        resp = self._esborra_bloc([lliure, cosit])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [lliure])
        self.assertEqual(
            resp.data['retinguts'],
            [{'id': cosit, 'motiu': 'en_us', 'sew_relations': [rel.id]}],
        )
        self.assertFalse(PatternSegment.objects.filter(pk=lliure).exists())
        self.assertTrue(PatternSegment.objects.filter(pk=cosit).exists())

    def test_un_id_que_no_existeix_no_peta_el_bloc(self):
        """Mai 500: un id fantasma és una resposta de l'informe, no una avaria."""
        a = self._declara(self.punts[3], self.punts[33]).data['id']

        resp = self._esborra_bloc([a, 999999])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [a])
        self.assertEqual(resp.data['retinguts'], [{'id': 999999, 'motiu': 'no_trobat'}])

    def test_un_bloc_sense_ids_es_400(self):
        resp = self._esborra_bloc([])

        self.assertEqual(resp.status_code, 400)

    def test_la_costura_veu_el_solapament_al_seu_detall(self):
        """La validació de cobertura viatja al detall de la costura: dues costures que
        reclamen el mateix tros de vora ho canten, amb els centímetres."""
        a = self._declara(self.punts[3], self.punts[40], nom='lateral').data['id']
        b = self._declara(self.punts[30], self.punts[60], nom='sisa').data['id']

        r1 = SewRelation.objects.create(model=self.model, tipus='casat')
        r1.segments_a.add(a)
        r1.segments_b.add(self.tram_back)
        # Cada costura amb el SEU tram d'esquena: si les dues compartissin el mateix,
        # l'esquena també sortiria solapada (correctament) i taparia el que aquí es prova.
        r2 = SewRelation.objects.create(model=self.model, tipus='casat')
        r2.segments_a.add(b)
        r2.segments_b.add(self.tram_back_2)

        estat = comprovar_costura(r1)

        solap = [c for c in estat['cobertura'] if c['mena'] == MENA_SOLAPAMENT]
        self.assertTrue(solap, estat['cobertura'])
        self.assertGreater(solap[0]['solapament_cm'], 0)
        self.assertEqual(sorted(solap[0]['sews']), sorted([r1.id, r2.id]))
        self.assertEqual(solap[0]['peca'], 'TATE_FRONT')

    def test_un_tram_que_dona_la_volta_no_mesura_zero(self):
        """El bug que els trams declarats destapen: la longitud d'un costat es calculava amb
        una resta, i un tram que passa per l'origen hi donava zero."""
        volta = self._declara(self.punts[3], self.punts[33], arc_llarg=True).data['id']
        rel = SewRelation.objects.create(model=self.model, tipus='casat')
        rel.segments_a.add(volta)
        rel.segments_b.add(self.tram_back)

        estat = comprovar_costura(rel)

        self.assertGreater(estat['longitud_a_cm'], 0)


class LlistaDeTreballAPITest(PatternsAPITestBase):
    """`GET …/model-poms/`: les Mesures del model creuades amb el que el patró mesura.

    És la pregunta del taller: d'això que la fitxa mana, què he col·locat i quadra?
    """

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])
        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')
        self.girs = list(
            self.front.points.filter(mena='vertex', tipus='turn', boundary_index=0)
            .order_by('ordre'))

        self.pom_a = POMMaster.objects.create(codi_client='T.1', nom_client='Front rise')
        self.pom_b = POMMaster.objects.create(codi_client='CH', nom_client='Chest width')
        # Una mesura amb tolerància pròpia i una altra sense (que ha de caure al catàleg).
        self.bm_a = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_a, base_value_cm=50.0, nom_fitxa='A',
            tolerancia_minus=Decimal('1.00'), tolerancia_plus=Decimal('1.00'), ordre=1)
        self.bm_b = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_b, base_value_cm=45.0, nom_fitxa='CH', ordre=2)

    def _llista(self, pk=None):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{pk or self.fp.id}/model-poms/')
        force_authenticate(request, user=self.user)
        return PatternFileViewSet.as_view({'get': 'model_poms'})(
            request, pk=pk or self.fp.id)

    def _ancora(self, pom, a, b):
        request = self.factory.post('/api/v1/patterns/pattern-poms/', {
            'pattern_piece': self.front.id, 'pom_master': pom.id,
            'definicio_mesura': {'mode': 'points', 'a': a.id, 'b': b.id},
            'metode': 'recta',
        }, format='json')
        force_authenticate(request, user=self.user)
        return PatternPOMViewSet.as_view({'post': 'create'})(request)

    def test_sense_cap_ancoratge_totes_les_mesures_surten_pendents(self):
        resp = self._llista()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total'], 2)
        self.assertEqual(resp.data['ancorats'], 0)
        for fila in resp.data['results']:
            self.assertFalse(fila['ancorat'])
            self.assertIsNone(fila['valor_mesurat_cm'])
            self.assertIsNone(fila['delta_cm'])
            self.assertIsNone(fila['dins_tolerancia'])

    def test_la_fila_porta_el_que_la_fitxa_mana(self):
        fila = next(f for f in self._llista().data['results'] if f['codi_client'] == 'T.1')

        self.assertEqual(fila['nom_fitxa'], 'A')
        self.assertEqual(fila['nom_client'], 'Front rise')
        self.assertEqual(fila['valor_fitxa_cm'], 50.0)
        self.assertEqual(fila['pom_master'], self.pom_a.id)

    def test_ancorar_un_pom_omple_la_seva_fila_amb_la_diferencia(self):
        """La Δ és tot el que això persegueix: el patró mesura X, la fitxa en deia Y."""
        anc = self._ancora(self.pom_a, self.girs[0], self.girs[3])
        self.assertEqual(anc.status_code, 201)
        mesurat = anc.data['valor_mesurat_cm']

        resp = self._llista()
        fila = next(f for f in resp.data['results'] if f['codi_client'] == 'T.1')

        self.assertEqual(resp.data['ancorats'], 1)
        self.assertTrue(fila['ancorat'])
        self.assertEqual(fila['peca'], 'TATE_FRONT')
        self.assertEqual(fila['pattern_pom'], anc.data['id'])
        self.assertEqual(fila['valor_mesurat_cm'], mesurat)
        self.assertEqual(fila['delta_cm'], round(mesurat - 50.0, 2))

    def test_la_tolerancia_de_la_mesura_mana_sobre_la_del_cataleg(self):
        files = {f['codi_client']: f for f in self._llista().data['results']}

        # T.1 la porta pròpia (1.0); CH no en té i cau a la del catàleg (0.6 per defecte).
        self.assertEqual(files['T.1']['tolerancia_minus_cm'], 1.0)
        self.assertEqual(files['T.1']['tolerancia_plus_cm'], 1.0)
        self.assertEqual(files['CH']['tolerancia_minus_cm'], 0.6)

    def test_dins_tolerancia_jutja_la_diferencia_amb_la_tolerancia_de_la_fila(self):
        anc = self._ancora(self.pom_a, self.girs[0], self.girs[3])
        mesurat = anc.data['valor_mesurat_cm']

        # La mesura de fitxa es mou fins a deixar la Δ JUST dins i JUST fora de ±1.0.
        BaseMeasurement.objects.filter(pk=self.bm_a.pk).update(base_value_cm=mesurat - 0.9)
        fila = next(f for f in self._llista().data['results'] if f['codi_client'] == 'T.1')
        self.assertTrue(fila['dins_tolerancia'])

        BaseMeasurement.objects.filter(pk=self.bm_a.pk).update(base_value_cm=mesurat - 1.4)
        fila = next(f for f in self._llista().data['results'] if f['codi_client'] == 'T.1')
        self.assertFalse(fila['dins_tolerancia'])

    def test_una_mesura_sense_valor_de_fitxa_es_mesura_pero_no_te_delta(self):
        """Un POM col·locat sobre una plantilla sense valor no s'inventa una comparació."""
        BaseMeasurement.objects.filter(pk=self.bm_a.pk).update(base_value_cm=None)
        self._ancora(self.pom_a, self.girs[0], self.girs[3])

        fila = next(f for f in self._llista().data['results'] if f['codi_client'] == 'T.1')

        self.assertTrue(fila['ancorat'])
        self.assertIsNotNone(fila['valor_mesurat_cm'])
        self.assertIsNone(fila['delta_cm'])
        self.assertIsNone(fila['dins_tolerancia'])

    def test_una_mesura_inactiva_no_es_feina(self):
        BaseMeasurement.objects.filter(pk=self.bm_b.pk).update(is_active=False)

        resp = self._llista()

        self.assertEqual(resp.data['total'], 1)
        self.assertNotIn('CH', [f['codi_client'] for f in resp.data['results']])

    def test_un_patro_sense_model_no_te_fitxa_de_mesures(self):
        """L'altra branca del XOR (patró d'un GarmentTypeItem): es diu, no es fingeix."""
        fp_item = PatternFile.objects.get(pk=self._upload(
            TATE_DXF.read_bytes(), model='', garment_type_item=self.item.id).data['id'])

        resp = self._llista(pk=fp_item.id)

        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.data)


class PincaAPITest(PatternsAPITestBase):
    """El gest de marcar una pinça, i el que en surt — amb el TATE real (W4b).

    El cas del banc, sencer i pel camí de l'API: la costura lateral del TATE uneix un tram
    del davanter de 32.13 cm amb un de l'esquena de 29.80. NO casa per 2.33 cm i el patró és
    correcte: al mig del davanter hi ha una pinça. Es marca (tres clics), i la costura casa.
    """

    # Els vèrtexs del TATE, sobre la vora de cosit. Els mateixos que PincaTest.
    TRAM_INICI, TRAM_FI = 68, 72
    PINCA_A, PINCA_VERTEX, PINCA_B = 69, 70, 71
    BACK_INICI, BACK_FI = 165, 167

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])

        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')
        self.vora_front = (self.front.segments
                           .filter(origen=PatternSegment.ORIGEN_AUTO).first().vora)
        self.pf = list(self.front.points
                       .filter(mena='vertex', boundary_index=self.vora_front).order_by('ordre'))

        self.back = self.fp.pieces.get(nom_block='TATE_BACK')
        self.vora_back = (self.back.segments
                          .filter(origen=PatternSegment.ORIGEN_AUTO).first().vora)
        self.pb = list(self.back.points
                       .filter(mena='vertex', boundary_index=self.vora_back).order_by('ordre'))

    # ── els gestos, per l'API ───────────────────────────────────────────────
    def _tram(self, a, b, nom):
        request = self.factory.post(
            '/api/v1/patterns/pattern-segments/',
            {'point_a': a.id, 'point_b': b.id, 'nom': nom}, format='json')
        force_authenticate(request, user=self.user)
        return PatternSegmentViewSet.as_view({'post': 'create'})(request)

    def _marca_pinca(self, **extra):
        dades = {
            'model': self.model.id,
            'point_a': self.pf[self.PINCA_A].id,
            'point_vertex': self.pf[self.PINCA_VERTEX].id,
            'point_b': self.pf[self.PINCA_B].id,
            'nom': 'Pinça 1', 'nom_a': 'Pinça 1 · costat A', 'nom_b': 'Pinça 1 · costat B',
        }
        dades.update(extra)
        request = self.factory.post('/api/v1/patterns/sew-relations/pinca/', dades,
                                    format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'pinca'})(request)

    def _cus_el_lateral(self):
        """La costura lateral del banc: davanter (amb la pinça a dins) contra esquena."""
        a = self._tram(self.pf[self.TRAM_INICI], self.pf[self.TRAM_FI], 'Lateral davanter')
        b = self._tram(self.pb[self.BACK_INICI], self.pb[self.BACK_FI], 'Lateral esquena')
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/',
            {'model': self.model.id, 'segments_a': [a.data['id']],
             'segments_b': [b.data['id']], 'tipus': 'casat', 'diferencial_cm': 0},
            format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'create'})(request)

    # ── T1: el gest ─────────────────────────────────────────────────────────
    def test_tres_clics_fan_dos_trams_i_una_costura_de_pinca(self):
        """Cap model nou: una pinça ÉS dos trams declarats i una SewRelation que els cus."""
        resp = self._marca_pinca()

        self.assertEqual(resp.status_code, 201, resp.data)
        rel = SewRelation.objects.get(pk=resp.data['id'])
        self.assertEqual(rel.tipus, SewRelation.TIPUS_PINCA)
        self.assertEqual(rel.nom, 'Pinça 1')
        self.assertTrue(resp.data['es_pinca'])

        costats = list(rel.segments_a.all()) + list(rel.segments_b.all())
        self.assertEqual(len(costats), 2)
        for c in costats:
            self.assertEqual(c.origen, PatternSegment.ORIGEN_DECLARAT)
            self.assertEqual(c.piece_id, self.front.id)
            self.assertEqual(c.vora, self.vora_front)
        self.assertEqual([c.nom for c in costats],
                         ['Pinça 1 · costat A', 'Pinça 1 · costat B'])

    def test_els_dos_costats_de_la_pinca_del_tate_sumen_2_34(self):
        self._marca_pinca()
        rel = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)

        estat = comprovar_costura(rel)

        # Els costats reals del TATE: 1.33 i 1.01. La pinça no és simètrica, i el motor no ho
        # amaga — és el patró qui ho diu.
        suma = estat['longitud_a_cm'] + estat['longitud_b_cm']
        self.assertAlmostEqual(suma, 2.34, places=2)

    def test_un_gest_que_falla_no_deixa_trams_orfes(self):
        """Un gest que l'usuari viu com un de sol no pot deixar mitja cosa feta.

        I falla amb un 400, no amb una avaria: si el model es deixés comprovar a la FK de la
        BD, això seria un IntegrityError (un 500) a mig gest. La transacció faria igualment el
        seu paper —cap tram orfe—, però l'usuari rebria una avaria en comptes d'un motiu.
        """
        resp = self._marca_pinca(model=999999)   # el model no existeix

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(
            PatternSegment.objects.filter(origen=PatternSegment.ORIGEN_DECLARAT).exists())

    def test_una_pinca_amb_un_punt_repetit_no_es_cap_pinca(self):
        resp = self._marca_pinca(point_b=self.pf[self.PINCA_A].id)

        self.assertEqual(resp.status_code, 400)

    # ── T2: el descompte, pel camí de l'API ─────────────────────────────────
    def test_sense_la_pinca_declarada_el_lateral_del_tate_NO_casa(self):
        """El punt de partida: el patró és bo i el motor el suspèn."""
        resp = self._cus_el_lateral()

        estat = resp.data['estat']
        self.assertFalse(estat['casa'])
        self.assertAlmostEqual(estat['desviament_cm'], 2.33, places=2)

    def test_marcada_la_pinca_el_lateral_del_tate_CASA_i_diu_laritmetica(self):
        """El cas del banc, sencer. I l'operació a la vista: 32.13 − 2.34 = 29.79."""
        sew = self._cus_el_lateral()
        self._marca_pinca()

        rel = SewRelation.objects.get(pk=sew.data['id'])
        estat = comprovar_costura(rel)

        self.assertTrue(estat['casa'])
        self.assertAlmostEqual(estat['brut_a_cm'], 32.13, places=2)     # el contorn
        self.assertAlmostEqual(estat['longitud_a_cm'], 29.79, places=2)  # el que es cus
        self.assertAlmostEqual(estat['longitud_b_cm'], 29.80, places=2)
        self.assertEqual(len(estat['descomptes_a']), 1)
        self.assertEqual(estat['descomptes_a'][0]['nom'], 'Pinça 1')
        self.assertAlmostEqual(estat['descomptes_a'][0]['cm'], 2.34, places=2)
        # L'esquena no té pinça: no se li descompta res.
        self.assertEqual(estat['descomptes_b'], [])

    def test_la_pinca_no_encen_cap_avis_de_cobertura_fals(self):
        """Els costats de la pinça viuen DINS del tram lateral. Sense l'excepció, la vora
        sortia amb solapament i amb excés — i està perfectament bé."""
        sew = self._cus_el_lateral()
        self._marca_pinca()

        rel = SewRelation.objects.get(pk=sew.data['id'])

        self.assertEqual(comprovar_costura(rel)['cobertura'], [])

    def test_una_pinca_no_es_descompta_a_ella_mateixa(self):
        """Els seus dos costats SÓN la costura: restar-los-hi deixaria una pinça de longitud
        zero, que casaria sempre. Un validador que sempre diu que sí no valida res."""
        self._marca_pinca()
        rel = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)

        estat = comprovar_costura(rel)

        self.assertEqual(estat['descomptes_a'], [])
        self.assertEqual(estat['descomptes_b'], [])
        self.assertGreater(estat['longitud_a_cm'], 0)

    # ── ESBORRAT EN BLOC del camí amb més risc (QA-TALLER E · T8) ───────────

    def _esborra_bloc_sew(self, ids):
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/bulk-delete/', {'ids': ids}, format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'bulk_delete'})(request)

    def test_el_bloc_sen_emporta_la_pinca_i_els_seus_dos_costats(self):
        """El camí amb més risc: la cascada de la pinça, dins d'un bloc.

        Els costats d'una pinça no existeixen sense ella. Si el bloc els deixés enrere, el
        patró s'ompliria de trams declarats que ningú no cus, amb nom de pinça i sense pinça
        —i continuarien sortint a la llista del que es pot cosir.
        """
        self._marca_pinca()
        rel = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)
        costats = [c.id for c in list(rel.segments_a.all()) + list(rel.segments_b.all())]
        self.assertEqual(len(costats), 2)

        resp = self._esborra_bloc_sew([rel.id])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [rel.id])
        self.assertFalse(SewRelation.objects.filter(pk=rel.id).exists())
        self.assertFalse(PatternSegment.objects.filter(pk__in=costats).exists())

    def test_un_costat_de_pinca_que_una_altra_costura_cus_es_queda(self):
        """El PROTECT val dins del bloc igual que fora: esborrar-lo deixaria coixa una costura
        que ningú ha tocat. La pinça cau; el costat en ús, no."""
        self._marca_pinca()
        rel = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)
        costats = list(rel.segments_a.all()) + list(rel.segments_b.all())
        altra = SewRelation.objects.create(model=self.model, tipus='casat')
        altra.segments_a.add(costats[0])

        resp = self._esborra_bloc_sew([rel.id])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [rel.id])
        self.assertTrue(PatternSegment.objects.filter(pk=costats[0].id).exists())
        self.assertFalse(PatternSegment.objects.filter(pk=costats[1].id).exists())

    def test_un_id_que_rebota_al_mig_no_sen_emporta_els_anteriors(self):
        """Èxit PARCIAL, i informe. El bloc no és «tot o res»: qui n'ha demanat tres no ha
        demanat que el segon en salvi dos. I mai un 500 —un id fantasma és una resposta."""
        self._marca_pinca()
        pinca = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)
        altra = SewRelation.objects.create(model=self.model, tipus='casat')

        resp = self._esborra_bloc_sew([pinca.id, 999999, altra.id])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['esborrats'], [pinca.id, altra.id])
        self.assertEqual(resp.data['retinguts'], [{'id': 999999, 'motiu': 'no_trobat'}])
        self.assertFalse(
            SewRelation.objects.filter(pk__in=[pinca.id, altra.id]).exists())

    def test_una_pinca_entre_dues_peces_no_es_una_pinca_de_vora(self):
        """`es_pinca_de_vora` es constata de la geometria, no d'un flag: una 'pinca' amb un
        costat a cada peça és una instrucció de muntatge, i no descompta tela de ningú."""
        a = self._tram(self.pf[self.TRAM_INICI], self.pf[self.TRAM_FI], 'davant')
        b = self._tram(self.pb[self.BACK_INICI], self.pb[self.BACK_FI], 'esquena')
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/',
            {'model': self.model.id, 'segments_a': [a.data['id']],
             'segments_b': [b.data['id']], 'tipus': 'pinca', 'diferencial_cm': 2.33},
            format='json')
        force_authenticate(request, user=self.user)
        resp = SewRelationViewSet.as_view({'post': 'create'})(request)

        self.assertFalse(resp.data['es_pinca'])

    def test_esborrar_una_pinca_se_nemporta_els_seus_dos_costats(self):
        """Els costats d'una pinça SÓN la pinça: no existeixen sense ella. Deixar-los enrere
        ompliria el patró de trams que ningú no cus i que ningú no sabria d'on venen."""
        resp = self._marca_pinca()
        rel_id = resp.data['id']
        self.assertEqual(
            PatternSegment.objects.filter(origen=PatternSegment.ORIGEN_DECLARAT).count(), 2)

        request = self.factory.delete(f'/api/v1/patterns/sew-relations/{rel_id}/')
        force_authenticate(request, user=self.user)
        r = SewRelationViewSet.as_view({'delete': 'destroy'})(request, pk=rel_id)

        self.assertEqual(r.status_code, 204)
        self.assertFalse(SewRelation.objects.filter(pk=rel_id).exists())
        self.assertFalse(
            PatternSegment.objects.filter(origen=PatternSegment.ORIGEN_DECLARAT).exists())

    def test_esborrar_una_costura_normal_NO_toca_els_seus_trams(self):
        """La cascada és de la PINÇA, no de qualsevol costura: un tram declarat és vocabulari
        del patró i sobreviu a la costura que el feia servir."""
        sew = self._cus_el_lateral()
        request = self.factory.delete(f'/api/v1/patterns/sew-relations/{sew.data["id"]}/')
        force_authenticate(request, user=self.user)

        SewRelationViewSet.as_view({'delete': 'destroy'})(request, pk=sew.data['id'])

        self.assertEqual(
            PatternSegment.objects.filter(origen=PatternSegment.ORIGEN_DECLARAT).count(), 2)

    # ── T5b: recol·locar ────────────────────────────────────────────────────
    def test_recol_locar_un_tram_EN_US_el_mou_sobre_la_mateixa_fila(self):
        """El PROTECT és per a ESBORRAR. Un tram mal posat s'ha de poder arreglar sense
        desmuntar la costura que el fa servir — i la costura es revalida sola."""
        sew = self._cus_el_lateral()
        rel = SewRelation.objects.get(pk=sew.data['id'])
        tram = rel.segments_a.first()
        abans = (tram.t_inici, tram.t_fi)

        request = self.factory.patch(
            f'/api/v1/patterns/pattern-segments/{tram.id}/',
            {'point_a': self.pf[self.TRAM_INICI].id, 'point_b': self.pf[self.PINCA_B].id},
            format='json')
        force_authenticate(request, user=self.user)
        resp = PatternSegmentViewSet.as_view({'patch': 'update'})(request, pk=tram.id)

        self.assertEqual(resp.status_code, 200, resp.data)
        tram.refresh_from_db()
        # MATEIXA fila (mai esborrar-i-crear: les costures la referencien).
        self.assertEqual(tram.id, rel.segments_a.first().id)
        self.assertNotEqual((tram.t_inici, tram.t_fi), abans)
        # I la costura ho ha notat: el costat A ara és més curt.
        self.assertLess(comprovar_costura(rel)['longitud_a_cm'], 32.13)

    def test_un_tram_no_pot_saltar_de_peca(self):
        """Canviar-lo de peça el faria un altre tram, i les costures que el cusen es
        trobarien cosint una altra peça sense que ningú els ho hagués dit."""
        a = self._tram(self.pf[self.TRAM_INICI], self.pf[self.TRAM_FI], 'lateral')

        request = self.factory.patch(
            f'/api/v1/patterns/pattern-segments/{a.data["id"]}/',
            {'point_a': self.pb[self.BACK_INICI].id, 'point_b': self.pb[self.BACK_FI].id},
            format='json')
        force_authenticate(request, user=self.user)
        resp = PatternSegmentViewSet.as_view({'patch': 'update'})(request, pk=a.data['id'])

        self.assertEqual(resp.status_code, 400)

    # ── T6: el bateig ───────────────────────────────────────────────────────
    def test_el_bateig_de_la_costura_es_conserva(self):
        """El nom generat NO es desa (seria un string congelat): només el que algú tria."""
        sew = self._cus_el_lateral()
        rel = SewRelation.objects.get(pk=sew.data['id'])

        self.assertEqual(rel.nom, '')            # sense bateig: el nom se'l genera el client

        request = self.factory.patch(
            f'/api/v1/patterns/sew-relations/{rel.id}/', {'nom': 'Costura lateral dreta'},
            format='json')
        force_authenticate(request, user=self.user)
        resp = SewRelationViewSet.as_view({'patch': 'partial_update'})(request, pk=rel.id)

        self.assertEqual(resp.status_code, 200, resp.data)
        rel.refresh_from_db()
        self.assertEqual(rel.nom, 'Costura lateral dreta')


class AcceptacioToleranciaAPITest(PincaAPITest):
    """El tècnic accepta un desajust, amb rastre append-only (QA-TALLER H · T2).

    Hereta de PincaAPITest perquè marcar una pinça del TATE ja dona una relació amb desajust
    (els costats fan 1,33 i 1,01 cm → 3,2 mm → grau vermell), que és el que es pot acceptar.
    """

    def _accio(self, sew_id, accio, nota=''):
        req = self.factory.post(
            '/api/v1/patterns/sew-tolerance-acceptances/',
            {'sew_relation': sew_id, 'accio': accio, 'nota': nota}, format='json')
        force_authenticate(req, user=self.user)
        return SewToleranceAcceptanceViewSet.as_view({'post': 'create'})(req)

    def _estat_sew(self, sew_id):
        rel = SewRelation.objects.get(pk=sew_id)
        return SewRelationSerializer(rel).data

    def _pinca_amb_desajust(self):
        self._marca_pinca()
        rel = SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA)
        self.assertEqual(comprovar_costura(rel)['grau'], 'err',
                         'la pinça del TATE ha de tenir desajust per poder-se acceptar')
        return rel

    def test_acceptar_congela_el_desajust_i_el_llindar(self):
        rel = self._pinca_amb_desajust()

        resp = self._accio(rel.id, 'accepta', nota='el patró és correcte, la pinça tanca bé')

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['accio'], 'accepta')
        self.assertEqual(resp.data['grau'], 'err')
        self.assertEqual(resp.data['tipus_relacio'], 'pinca')
        self.assertEqual(resp.data['mena_tolerancia'], 'pinca')
        self.assertEqual((resp.data['llindar_verd_mm'], resp.data['llindar_groc_mm']), (1.5, 3.0))
        self.assertGreater(resp.data['desajust_cm'], 0.3)
        self.assertEqual(resp.data['sew_relation_snapshot'], rel.id)
        # La costura ara diu, inline, que està acceptada i per qui.
        acc = self._estat_sew(rel.id)['acceptacio']
        self.assertTrue(acc['acceptat'])
        self.assertEqual(acc['grau'], 'err')

    def test_desacceptar_es_un_esdeveniment_nou_no_un_esborrat(self):
        rel = self._pinca_amb_desajust()
        self._accio(rel.id, 'accepta')

        resp = self._accio(rel.id, 'desaccepta', nota='ho reviso millor')

        self.assertEqual(resp.status_code, 201)
        # Dos esdeveniments a l'històric; l'estat viu és «no acceptat».
        self.assertEqual(SewToleranceAcceptance.objects.filter(sew_relation=rel).count(), 2)
        self.assertIsNone(self._estat_sew(rel.id)['acceptacio'])

    def test_el_registre_es_APPEND_ONLY(self):
        rel = self._pinca_amb_desajust()
        self._accio(rel.id, 'accepta')
        ev = SewToleranceAcceptance.objects.filter(sew_relation=rel).first()

        with self.assertRaises(ValueError):
            ev.nota = 'reescrit'
            ev.save()
        with self.assertRaises(ValueError):
            ev.delete()
        with self.assertRaises(ValueError):
            SewToleranceAcceptance.objects.filter(sew_relation=rel).delete()

    def test_no_es_pot_acceptar_una_costura_verda(self):
        # Una costura casada dins tolerància (grau ok) no té res a acceptar.
        a = self._tram(self.pf[self.TRAM_INICI], self.pf[self.TRAM_FI], 'A')
        b = self._tram(self.pf[self.TRAM_INICI], self.pf[self.TRAM_FI], 'B')
        req = self.factory.post(
            '/api/v1/patterns/sew-relations/',
            {'model': self.model.id, 'segments_a': [a.data['id']],
             'segments_b': [b.data['id']], 'tipus': 'casat', 'diferencial_cm': 0},
            format='json')
        force_authenticate(req, user=self.user)
        sew = SewRelationViewSet.as_view({'post': 'create'})(req)
        self.assertEqual(comprovar_costura(SewRelation.objects.get(pk=sew.data['id']))['grau'],
                         'ok')

        resp = self._accio(sew.data['id'], 'accepta')

        self.assertEqual(resp.status_code, 400)

    def test_ni_acceptar_dues_vegades_ni_desacceptar_el_que_no_hi_es(self):
        rel = self._pinca_amb_desajust()

        self.assertEqual(self._accio(rel.id, 'desaccepta').status_code, 400)  # encara no acceptat
        self._accio(rel.id, 'accepta')
        self.assertEqual(self._accio(rel.id, 'accepta').status_code, 400)     # ja acceptat

    def test_lauditoria_es_llegeix_per_model(self):
        rel = self._pinca_amb_desajust()
        self._accio(rel.id, 'accepta')
        self._accio(rel.id, 'desaccepta')

        req = self.factory.get(
            '/api/v1/patterns/sew-tolerance-acceptances/', {'model': self.model.id})
        force_authenticate(req, user=self.user)
        resp = SewToleranceAcceptanceViewSet.as_view({'get': 'list'})(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 2)   # tot l'històric, transversal per model


class GeometriaPortaElsTramsDeclaratsTest(PatternsAPITestBase):
    """La geometria ha de dir, d'un tram, si és una PROPOSTA del motor o una DECLARACIÓ.

    Sense `origen`/`nom` a la geometria, el taller havia de fer una segona crida per saber
    què podia cosir: dues peticions per a una sola pregunta.
    """

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])
        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')

    def _geometria(self):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/geometry/')
        force_authenticate(request, user=self.user)
        resp = PatternFileViewSet.as_view({'get': 'geometry'})(request, pk=self.fp.id)
        return next(p for p in resp.data['pieces'] if p['nom_block'] == 'TATE_FRONT')

    def test_els_trams_del_motor_surten_derivats_i_sense_nom(self):
        """El motor en fa DUES lectures (`auto` i `natural`) i cap no és una decisió de
        ningú: derivat vol dir, exactament, que no l'ha batejat cap persona."""
        derivats = {PatternSegment.ORIGEN_AUTO, PatternSegment.ORIGEN_NATURAL}
        trams = self._geometria()['segments']
        self.assertTrue(trams)
        for seg in trams:
            self.assertIn(seg['origen'], derivats)
            self.assertIsNone(seg['nom'])
        # I les dues lectures hi són: si una deixés de generar-se, el bucle de sobre
        # seguiria passant sense dir res.
        self.assertEqual({s['origen'] for s in trams}, derivats)

    def test_un_tram_declarat_surt_amb_el_seu_origen_i_el_seu_nom(self):
        punts = list(self.front.points.filter(mena='vertex', boundary_index=0)
                     .order_by('ordre'))
        request = self.factory.post('/api/v1/patterns/pattern-segments/', {
            'point_a': punts[0].id, 'point_b': punts[4].id, 'nom': 'costura lateral',
        }, format='json')
        force_authenticate(request, user=self.user)
        creat = PatternSegmentViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(creat.status_code, 201)

        seg = next(s for s in self._geometria()['segments'] if s['id'] == creat.data['id'])

        self.assertEqual(seg['origen'], PatternSegment.ORIGEN_DECLARAT)
        self.assertEqual(seg['nom'], 'costura lateral')


class TokenFrescAlClicTest(PatternsAPITestBase):
    """El token es demana al CLIC, no es couva amb la pàgina (Taller W5 · fix D9).

    L'URL signada caduca als DOWNLOAD_TTL (900 s). Pintar-la al render vol dir que qui obre el
    patró i es posa a treballar —el cas NORMAL al Taller— es troba, mitja hora després, un botó
    que no descarrega res. El fix no és allargar el TTL (això és regalar el permís): és tornar a
    demanar-lo quan es fa servir.
    """

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(pk=self._upload(
            AMELIA_DXF.read_bytes(), AMELIA_RUL.read_bytes()).data['id'])

    def _links(self, pk):
        request = self.factory.get(f'/api/v1/patterns/pattern-files/{pk}/download-links/')
        force_authenticate(request, user=self.user)
        return PatternFileViewSet.as_view({'get': 'download_links'})(request, pk=pk)

    def _baixa(self, pk, token, accio='download_signed', url='download-signed'):
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{pk}/{url}/', {'token': token})
        return PatternFileViewSet.as_view({'get': accio})(request, pk=pk)

    @staticmethod
    def _token_de(url):
        return url.split('token=')[1]

    def test_el_token_couvat_al_render_es_mor_i_el_fresc_no(self):
        """EL CAS DE D9, sencer. Es pinta la pàgina, passen 16 minuts, i:
          · el token que es va signar al render → CADUCAT (és el botó mort que veia el QA)
          · el que es demana AL CLIC, en aquell mateix instant → viu.
        """
        # t=0: la pàgina es pinta i el detall porta la seva URL signada.
        couvat = self._token_de(self._links(self.fp.id).data['download_url'])

        # t = +16 min: l'usuari ha estat treballant amb el tab obert.
        setze_min = time.time() + 960          # 960 s > DOWNLOAD_TTL (900)
        with mock.patch('django.core.signing.time.time', return_value=setze_min):
            self.assertEqual(
                self._baixa(self.fp.id, couvat).status_code, 403,
                'El token couvat al render hauria d\'haver caducat: si no, el TTL no serveix.')

            # …i ara clica. El token es demana ARA, i ARA val.
            fresc = self._token_de(self._links(self.fp.id).data['download_url'])
            self.assertNotEqual(fresc, couvat)
            self.assertEqual(
                self._baixa(self.fp.id, fresc).status_code, 200,
                'El token demanat al clic ha de servir el fitxer al moment.')

    def test_el_rul_tambe_es_refresca(self):
        couvat = self._token_de(self._links(self.fp.id).data['download_rul_url'])
        setze_min = time.time() + 960
        with mock.patch('django.core.signing.time.time', return_value=setze_min):
            self.assertEqual(
                self._baixa(self.fp.id, couvat, 'download_rul_signed', 'download-rul-signed')
                .status_code, 403)
            fresc = self._token_de(self._links(self.fp.id).data['download_rul_url'])
            self.assertEqual(
                self._baixa(self.fp.id, fresc, 'download_rul_signed', 'download-rul-signed')
                .status_code, 200)

    def test_demanar_token_NO_serveix_bytes(self):
        """L'acció és read-only: torna URLs, no el fitxer. Si servís bytes seria una segona
        porta de descàrrega, i n'hi ha prou amb una."""
        resp = self._links(self.fp.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.data), {'download_url', 'download_rul_url', 'ttl_segons'})
        self.assertEqual(resp.data['ttl_segons'], DOWNLOAD_TTL)

    def test_qui_no_esta_autenticat_no_en_treu_cap_token(self):
        """La porta de tokens està gated com la resta de lectures: si no, seria la manera més
        senzilla de saltar-se l'autenticació que els tokens protegeixen."""
        request = self.factory.get(
            f'/api/v1/patterns/pattern-files/{self.fp.id}/download-links/')
        resp = PatternFileViewSet.as_view({'get': 'download_links'})(request, pk=self.fp.id)

        self.assertIn(resp.status_code, (401, 403))


# ═════════════════════════════════════════════════════════════════════════════
# A2 — PROPOSTA DE COSITS: el matcher (engine pur)
# ═════════════════════════════════════════════════════════════════════════════

class _P:
    """Un punt qualsevol, que és tot el que `projectar` necessita."""

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)


def _cand(seg_id, peca_id, nom, llarg_cm, piquets=(), vora=0):
    return Candidat(
        segment_id=seg_id, piece_id=peca_id, piece_nom=nom, vora=vora,
        t_inici=0.0, t_fi=0.5, longitud_mm=llarg_cm * 10.0, piquets=tuple(piquets),
    )


class PiquetsSobreLaVoraTest(unittest.TestCase):
    """Situar un piquet: la projecció, i la deduplicació de les DUES còpies del CAD."""

    #: Un quadrat de 100×100 mm, obert (5 punts, l'últim tanca).
    QUADRAT = [_P(0, 0), _P(100, 0), _P(100, 100), _P(0, 100), _P(0, 0)]

    def test_un_piquet_sobre_la_vora_cau_a_la_seva_t(self):
        dist, t = projectar(self.QUADRAT, False, 50, 0)

        self.assertAlmostEqual(dist, 0.0, places=6)
        self.assertAlmostEqual(t, 50 / 400, places=4)   # 50 mm dels 400 del perímetre

    def test_un_piquet_apartat_de_la_vora_hi_projecta_perpendicular(self):
        """El bessó del piquet, el que seu sobre l'ALTRA línia: cau a la mateixa `t`."""
        dist, t = projectar(self.QUADRAT, False, 50, 7.5)

        self.assertAlmostEqual(dist, 7.5, places=6)
        self.assertAlmostEqual(t, 50 / 400, places=4)

    def test_les_dues_copies_del_mateix_piquet_es_dedupliquen(self):
        """El CAD escriu cada piquet DUES vegades (línia de tall i línia de cosit).

        Comptar-les dues vegades duplicaria el nombre de marques —que és justament el número
        que el senyal fort compara— i cap parella no casaria mai.
        """
        notches = [_P(50, 0), _P(50, 7.5)]   # el mateix piquet, les seves dues còpies

        piquets = piquets_de_la_vora(self.QUADRAT, False, notches, 400.0)

        self.assertEqual(len(piquets), 1)

    def test_dos_piquets_de_debo_NO_es_dedupliquen(self):
        notches = [_P(20, 0), _P(60, 0)]     # 40 mm de separació: són dos

        piquets = piquets_de_la_vora(self.QUADRAT, False, notches, 400.0)

        self.assertEqual(len(piquets), 2)

    def test_una_marca_interna_no_es_un_piquet_de_vora(self):
        """Una marca al mig de la peça (una butxaca, un plec) no és una marca de costura."""
        piquets = piquets_de_la_vora(self.QUADRAT, False, [_P(50, 50)], 400.0)

        self.assertEqual(piquets, ())


class PiquetsDelTramTest(unittest.TestCase):
    """Quins piquets són d'un tram, i on hi cauen (posició RELATIVA)."""

    def test_els_extrems_compten(self):
        """Al material real TOTS els piquets seuen sobre girs, i els girs delimiten els trams.

        Mirant només l'interior, cap tram no tindria mai cap piquet: el senyal fort no
        existiria.
        """
        s = piquets_del_tram((0.2, 0.5), t_inici=0.2, t_fi=0.5)

        self.assertEqual(s, (0.0, 1.0))

    def test_un_piquet_al_mig_cau_a_la_seva_fraccio(self):
        s = piquets_del_tram((0.35,), t_inici=0.2, t_fi=0.6)

        self.assertEqual(len(s), 1)
        self.assertAlmostEqual(s[0], 0.375, places=6)

    def test_un_piquet_de_fora_no_hi_es(self):
        self.assertEqual(piquets_del_tram((0.9,), t_inici=0.2, t_fi=0.5), ())

    def test_un_tram_que_passa_per_lorigen_es_mesura_donant_la_volta(self):
        """`t_fi` < `t_inici`: el tram travessa el punt on la polilínia tanca."""
        s = piquets_del_tram((0.95, 0.05), t_inici=0.9, t_fi=0.1)

        self.assertEqual(len(s), 2)
        self.assertAlmostEqual(s[0], 0.25, places=6)   # 0.95 dins de [0.9, 1.1]
        self.assertAlmostEqual(s[1], 0.75, places=6)


class CasenPiquetsTest(unittest.TestCase):
    """El senyal FORT, i el sentit."""

    def test_casen_en_el_mateix_sentit(self):
        casen, invertit, desv = casen_piquets((0.0, 0.5, 1.0), (0.0, 0.5, 1.0))

        self.assertTrue(casen)
        self.assertFalse(invertit)
        self.assertAlmostEqual(desv, 0.0)

    def test_casen_INVERTITS_perque_les_vores_es_cusen_encarades(self):
        """El que en un costat va del 0 a l'1, en l'altre va de l'1 al 0. És el cas NORMAL."""
        casen, invertit, desv = casen_piquets((0.0, 0.3, 1.0), (0.0, 0.7, 1.0))

        self.assertTrue(casen)
        self.assertTrue(invertit)
        self.assertAlmostEqual(desv, 0.0)

    def test_un_nombre_diferent_de_piquets_no_casa(self):
        casen, _, _ = casen_piquets((0.0, 0.5), (0.0, 0.4, 0.9))

        self.assertFalse(casen)

    def test_els_mateixos_piquets_massa_lluny_no_casen(self):
        casen, _, desv = casen_piquets((0.0, 0.2), (0.0, 0.4))

        self.assertFalse(casen)
        self.assertGreater(desv, TOL_PIQUET_S)


class GraduacioToleranciaTest(unittest.TestCase):
    """El semàfor del veredicte (QA-TALLER H · T1). Presentació, no motor.

    Els llindars són criteri d'ofici (afinable); el test fixa el COMPORTAMENT als límits, no els
    valors —si la Montse els mou, s'actualitza aquí a posta, no és una regressió muda."""

    def test_pinca_desigual_de_3_1_mm_es_vermella(self):
        # El cas del banc: la pinça del TATE té els costats a 3,1 mm → passa el groc (3,0).
        g = graduar('pinca', 0.31)
        self.assertEqual(g['grau'], 'err')
        self.assertEqual((g['verd_mm'], g['groc_mm']), (1.5, 3.0))

    def test_els_limits_de_cada_banda(self):
        # Verd inclou el límit; groc inclou el seu; per sobre, vermell.
        self.assertEqual(graduar('pinca', 0.15)['grau'], 'ok')     # 1,5 mm just
        self.assertEqual(graduar('pinca', 0.16)['grau'], 'warn')   # 1,6 mm
        self.assertEqual(graduar('pinca', 0.30)['grau'], 'warn')   # 3,0 mm just
        self.assertEqual(graduar('pinca', 0.31)['grau'], 'err')
        self.assertEqual(graduar('casat', 0.20)['grau'], 'ok')     # 2,0 mm just
        self.assertEqual(graduar('casat', 0.41)['grau'], 'err')    # 4,1 mm

    def test_frunzit_no_te_gradient(self):
        # El diferencial del frunzit és intencional: no es gradua.
        g = graduar('frunzit', 1.5)
        self.assertEqual(g['grau'], 'na')
        self.assertIsNone(g['verd_mm'])

    def test_un_tipus_desconegut_cau_a_muntatge(self):
        # Val més graduar de menys que inventar-se una exigència no validada.
        g = graduar('mena-nova', 0.25)
        self.assertEqual(g['mena'], 'muntatge')
        self.assertEqual(g['grau'], 'ok')      # 2,5 mm ≤ 3,0 verd de muntatge


class SenyalLongitudTest(unittest.TestCase):
    """Casat, frunzit, o ni una cosa ni l'altra. I l'ORDRE en què es pregunta."""

    def test_iguals_dins_tolerancia_es_un_casat(self):
        senyal, tipus, dif = senyal_longitud(_cand(1, 1, 'A', 25.30), _cand(2, 2, 'B', 25.25))

        self.assertEqual(tipus, 'casat')
        self.assertEqual(dif, 0.0)
        self.assertGreater(senyal.punts, 0)

    def test_un_exces_sistematic_es_un_frunzit_i_el_diferencial_es_el_que_sha_mesurat(self):
        senyal, tipus, dif = senyal_longitud(_cand(1, 1, 'A', 30.0), _cand(2, 2, 'B', 27.0))

        self.assertEqual(tipus, 'frunzit')
        self.assertEqual(dif, 3.0)                       # 10%: dins del rang
        self.assertEqual(senyal.dades['sobra'], 'a')     # i diu QUIN costat sobra

    def test_dos_mil_limetres_sobre_deu_centimetres_NO_son_un_frunzit(self):
        """La tolerància ABSOLUTA es pregunta PRIMER, i per això aquest cas és un casat.

        2 mm sobre 10 cm són un 2% —dins del rang relatiu d'un frunzit— i no són cap frunzit:
        són el gruix del llapis. Declarar-los ensenyaria la cosidora a no fer cas dels
        diferencials, que és el pitjor que li pot passar a un.
        """
        senyal, tipus, dif = senyal_longitud(_cand(1, 1, 'A', 10.0), _cand(2, 2, 'B', 10.2))

        self.assertEqual(tipus, 'casat')
        self.assertEqual(dif, 0.0)

    def test_massa_diferents_es_evidencia_en_contra(self):
        senyal, _, _ = senyal_longitud(_cand(1, 1, 'A', 30.0), _cand(2, 2, 'B', 10.0))

        self.assertLess(senyal.punts, 0)


class SenyalNomsTest(unittest.TestCase):
    """El senyal feble: mai proposa sol, però sap dir que NO."""

    def test_front_amb_back_son_peces_veines(self):
        senyal = senyal_noms(_cand(1, 1, 'TATE_FRONT', 25), _cand(2, 2, 'TATE_BACK', 25))

        self.assertGreater(senyal.punts, 0)
        self.assertEqual(senyal.dades['motiu'], 'veines')

    def test_una_vista_es_cus_a_la_seva_peca(self):
        senyal = senyal_noms(
            _cand(1, 1, 'TATE_FACING_YOKE', 4), _cand(2, 2, 'TATE_FRONT_YOKE', 4))

        self.assertGreater(senyal.punts, 0)
        self.assertEqual(senyal.dades['motiu'], 'vista')

    def test_dues_peces_bessones_NO_es_cusen_luna_contra_laltra(self):
        """Una niada porta la màniga repetida. Per longitud casarien perfectament."""
        senyal = senyal_noms(_cand(1, 1, 'TATE_SLEEVE', 48), _cand(2, 2, '1rst_sleeve', 48))

        self.assertLess(senyal.punts, 0)
        self.assertEqual(senyal.dades['motiu'], 'bessones')

    def test_una_entretela_no_es_cus_es_termofixa(self):
        senyal = senyal_noms(
            _cand(1, 1, 'TATE_NECK_BAND', 9.9), _cand(2, 2, 'TATE_NECK_BAND_INTERLINING', 9.9))

        self.assertLess(senyal.punts, 0)
        self.assertEqual(senyal.dades['motiu'], 'entretela')

    def test_un_coll_i_una_maniga_es_coneixen_i_no_es_toquen(self):
        senyal = senyal_noms(_cand(1, 1, 'TATE_NECK_BAND', 11.5), _cand(2, 2, 'TATE_SLEEVE', 11.4))

        self.assertLess(senyal.punts, 0)
        self.assertEqual(senyal.dades['motiu'], 'llunyanes')

    def test_uns_noms_que_no_diem_res_no_pesen_ni_a_favor_ni_en_contra(self):
        """Un CAD que bateja les peces `PIEZA_1` no ha de deixar el motor mut: decideix la
        geometria. **No saber** i **saber que no** són coses diferents."""
        senyal = senyal_noms(_cand(1, 1, 'PIEZA_1', 25), _cand(2, 2, 'PIEZA_2', 25))

        self.assertEqual(senyal.punts, 0.0)


class ProposarTest(unittest.TestCase):
    """El repartiment: la llei de «cap tram a dues costures», i el rebuig."""

    def test_el_nom_MAI_proposa_sol(self):
        """Longituds incompatibles i noms perfectes: no hi ha proposta. La geometria mana."""
        a = _cand(1, 1, 'TATE_FRONT', 60.0)
        b = _cand(2, 2, 'TATE_BACK', 10.0)

        propostes, _ = proposar([a, b])

        self.assertEqual(propostes, [])

    def test_una_parella_amb_geometria_i_nom_es_proposa(self):
        a = _cand(1, 1, 'TATE_FRONT', 25.2, piquets=(0.0, 1.0))
        b = _cand(2, 2, 'TATE_BACK', 25.3, piquets=(0.0, 1.0))

        propostes, _ = proposar([a, b])

        self.assertEqual(len(propostes), 1)
        self.assertEqual(propostes[0].tipus, 'casat')
        self.assertGreaterEqual(propostes[0].confianca, LLINDAR_PROPOSTA)

    def test_cap_tram_no_va_a_dues_costures(self):
        """Dos pretendents per al mateix tram: se l'endú el de més confiança, i l'altre cau.

        Els dos pretendents han de ser propostes VÀLIDES (per sobre del llindar), o el que es
        provaria no seria el repartiment sinó el llindar: `fluix` casa en piquets i longitud, i
        només perd perquè el seu nom no diu res i el de `bo` sí.
        """
        a = _cand(1, 1, 'TATE_FRONT', 25.0, piquets=(0.0, 0.5, 1.0))
        bo = _cand(2, 2, 'TATE_BACK', 25.0, piquets=(0.0, 0.5, 1.0))     # + el nom hi juga
        fluix = _cand(3, 3, 'PIEZA_9', 25.0, piquets=(0.0, 0.5, 1.0))    # el nom calla

        propostes, desc = proposar([a, bo, fluix])

        self.assertEqual(len(propostes), 1)
        self.assertEqual(propostes[0].b.segment_id, bo.segment_id)
        # `fluix` no surt en cap proposta: els seus dos possibles companys (`a` i `bo`) han quedat
        # tots dos presos per la parella guanyadora, i per tant cauen les DUES parelles que en
        # depenien. La llei és «cap tram a dues costures», i es compleix a les dues bandes.
        vius = {s for p in propostes for s in (p.a.segment_id, p.b.segment_id)}
        self.assertNotIn(fluix.segment_id, vius)
        self.assertEqual(desc.en_conflicte, 2)

    def test_un_rebuig_treu_la_parella_pero_NO_bloqueja_els_seus_trams(self):
        """Dir que no a «màniga ⛓ màniga» ha de deixar la màniga lliure per a la parella bona."""
        a = _cand(1, 1, 'TATE_FRONT', 25.0, piquets=(0.0, 1.0))
        b = _cand(2, 2, 'TATE_BACK', 25.0, piquets=(0.0, 1.0))

        propostes, desc = proposar([a, b], exclosos=frozenset({clau_parella(1, 2)}))

        self.assertEqual(propostes, [])
        self.assertEqual(desc.rebutjades, 1)

    def test_la_clau_dune_parella_es_canonica(self):
        """Una costura no té costat A i costat B «de veritat»: la mateixa parella mirada de
        l'altra banda no pot tornar a sortir com si ningú no l'hagués rebutjada."""
        self.assertEqual(clau_parella(9, 4), clau_parella(4, 9))

    def test_dos_trams_de_la_MATEIXA_peca_no_es_proposen(self):
        """Els dos laterals de l'esquena fan exactament el mateix i NO es cusen l'un amb
        l'altre. Proposar-los seria omplir la llista de disbarats amb la màxima confiança."""
        a = _cand(1, 1, 'TATE_BACK', 25.3, piquets=(0.0, 1.0))
        b = _cand(2, 1, 'TATE_BACK', 25.3, piquets=(0.0, 1.0))

        propostes, _ = proposar([a, b])

        self.assertEqual(propostes, [])


class PropostesAPITest(PatternsAPITestBase):
    """A2 pel camí de l'API, amb el TATE real: proposar, confirmar, rebutjar.

    El banc és el fitxer de debò —10 peces, línia de cosit, 20 piquets al davanter— perquè el
    que ha de quedar demostrat no és que el matcher sàpiga sumar, sinó que sobre un patró
    industrial diu coses certes.
    """

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])

    # ── els gestos ──────────────────────────────────────────────────────────
    def _propostes(self):
        request = self.factory.get(
            '/api/v1/patterns/sew-relations/propostes/', {'model': self.model.id})
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'get': 'propostes'})(request)

    def _confirma(self, p, **extra):
        dades = {
            'model': self.model.id,
            'segment_a': p['a']['segment_id'], 'segment_b': p['b']['segment_id'],
            'tipus': p['tipus'], 'diferencial_cm': p['diferencial_cm'],
            'nom_a': 'Tram A', 'nom_b': 'Tram B',
        }
        dades.update(extra)
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/confirmar-proposta/', dades, format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'confirmar_proposta'})(request)

    def _rebutja(self, p, motiu=''):
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/rebutjar-proposta/',
            {'model': self.model.id, 'segment_a': p['a']['segment_id'],
             'segment_b': p['b']['segment_id'], 'motiu': motiu},
            format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'rebutjar_proposta'})(request)

    def _parella(self, propostes, peca_a, peca_b):
        """La proposta que uneix aquestes dues peces (en qualsevol ordre)."""
        for p in propostes:
            if {p['a']['peca'], p['b']['peca']} == {peca_a, peca_b}:
                return p
        return None

    # ── T2: la llista ───────────────────────────────────────────────────────
    def test_el_motor_proposa_la_lateral_del_TATE(self):
        """El davanter i l'esquena, pel costat: 25,3 contra 25,2 cm. La costura que hi és."""
        resp = self._propostes()

        self.assertEqual(resp.status_code, 200)
        lateral = self._parella(resp.data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        self.assertIsNotNone(lateral, 'la lateral FRONT↔BACK no s\'ha proposat')
        self.assertEqual(lateral['tipus'], 'casat')
        self.assertGreater(lateral['confianca'], 0.7)

    def test_cada_proposta_porta_el_DESGLOS_dels_senyals(self):
        """Una confiança sola («87%») no es pot discutir. El desglòs, sí.

        Els tres de sempre hi són SEMPRE. El costum del taller (T4) només si diu alguna cosa:
        un senyal de zero punts i sense frase no es podria discutir, que és per al que serveix
        el desglòs."""
        p = self._propostes().data['propostes'][0]

        self.assertEqual({s['mena'] for s in p['senyals']}, {'piquets', 'longitud', 'noms'})
        for senyal in p['senyals']:
            self.assertIn('dades', senyal)
            self.assertTrue(senyal['detall'])

    def test_cada_proposta_diu_qUE_PASSARIA_si_es_confirmes(self):
        """El veredicte, calculat amb el mateix motor que després jutjarà la costura."""
        p = self._propostes().data['propostes'][0]

        self.assertIn('casa', p['veredicte'])
        self.assertIn('missatge', p['veredicte'])

    def test_proposar_NO_escriu_res(self):
        """La llei del paquet: proposar, mai escriure."""
        abans = (SewRelation.objects.count(), PatternSegment.objects.count())

        self._propostes()

        self.assertEqual(abans, (SewRelation.objects.count(), PatternSegment.objects.count()))

    def test_els_descartats_es_DIUEN(self):
        """Un matcher que amaga el que ha tirat menteix sobre la seva cobertura."""
        resp = self._propostes()

        self.assertGreater(resp.data['descartats']['curts'], 0)
        self.assertIn('sota_llindar', resp.data['descartats'])
        self.assertGreater(resp.data['candidats'], 0)

    # ── T3: confirmar ───────────────────────────────────────────────────────
    def test_confirmar_deixa_EXACTAMENT_el_que_deixaria_el_gest_manual(self):
        """Dos trams DECLARATS i una costura que els uneix. Ni una entitat de segona."""
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')

        resp = self._confirma(p)

        self.assertEqual(resp.status_code, 201, resp.data)
        rel = SewRelation.objects.get(pk=resp.data['id'])
        costats = list(rel.segments_a.all()) + list(rel.segments_b.all())
        self.assertEqual(len(costats), 2)
        for seg in costats:
            self.assertEqual(seg.origen, PatternSegment.ORIGEN_DECLARAT)
        self.assertEqual([s.nom for s in costats], ['Tram A', 'Tram B'])

    def test_confirmar_PROMOU_el_tram_i_no_toca_la_hipotesi_del_CAD(self):
        """El tram derivat es queda on és: és la lectura del CAD, no una decisió de ningú.

        A2 proposa sobre els NATURALS (T3b), així que la hipòtesi que no s'ha de tocar és
        aquella; el que ha de néixer és un tram DECLARAT a part."""
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        derivat_a = p['a']['segment_id']
        self.assertEqual(
            PatternSegment.objects.get(pk=derivat_a).origen,
            PatternSegment.ORIGEN_NATURAL)

        resp = self._confirma(p)
        self.assertEqual(resp.status_code, 201, resp.data)

        self.assertEqual(
            PatternSegment.objects.get(pk=derivat_a).origen,
            PatternSegment.ORIGEN_NATURAL)

    def test_confirmar_una_proposta_RECALCULA_les_altres(self):
        """La cobertura canvia: els trams que la costura nova reclama surten de la subhasta."""
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        claus_abans = {tuple(x['clau']) for x in self._propostes().data['propostes']}

        self._confirma(p)

        resp = self._propostes()
        claus = {tuple(x['clau']) for x in resp.data['propostes']}
        self.assertIn(tuple(p['clau']), claus_abans)
        self.assertNotIn(tuple(p['clau']), claus)
        self.assertGreater(resp.data['descartats']['ja_cosits'], 0)

    def test_no_es_pot_confirmar_una_proposta_sobre_un_tram_ja_DECLARAT(self):
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        self._confirma(p)
        declarat = PatternSegment.objects.filter(
            origen=PatternSegment.ORIGEN_DECLARAT).first()

        resp = self._confirma(p, segment_a=declarat.id)

        self.assertEqual(resp.status_code, 400)

    # ── T3: rebutjar ────────────────────────────────────────────────────────
    def test_un_rebuig_es_PERSISTENT(self):
        """Una eina que torna a proposar el que ja li han dit que no ensenya a no mirar-la."""
        p = self._propostes().data['propostes'][0]

        resp = self._rebutja(p, motiu='això no es cus')

        self.assertEqual(resp.status_code, 201)
        claus = {tuple(x['clau']) for x in self._propostes().data['propostes']}
        self.assertNotIn(tuple(p['clau']), claus)

    def test_un_rebuig_NO_bloqueja_els_trams_de_la_parella(self):
        """El que es rebutja és la PARELLA. Els seus trams queden lliures per a la bona."""
        p = self._propostes().data['propostes'][0]

        self._rebutja(p)

        resp = self._propostes()
        vius = {s for x in resp.data['propostes']
                for s in (x['a']['segment_id'], x['b']['segment_id'])}
        # Els trams d'una proposta rebutjada continuen sent candidats: el motor els torna a
        # oferir contra un altre company (o els descarta per confiança, però no per càstig).
        self.assertEqual(
            SewProposalRejection.objects.count(), 1)
        self.assertTrue(vius or resp.data['candidats'] > 0)

    def test_rebutjar_dues_vegades_no_duplica_el_rebuig(self):
        p = self._propostes().data['propostes'][0]
        self._rebutja(p)

        resp = self._rebutja(p)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['ja_hi_era'])
        self.assertEqual(SewProposalRejection.objects.count(), 1)

    def test_el_rebuig_es_desa_amb_la_clau_CANONICA(self):
        """La mateixa parella, mirada de l'altra banda, no pot tornar a sortir."""
        p = self._propostes().data['propostes'][0]

        request = self.factory.post(
            '/api/v1/patterns/sew-relations/rebutjar-proposta/',
            {'model': self.model.id,
             'segment_a': p['b']['segment_id'],      # a l'inrevés, a posta
             'segment_b': p['a']['segment_id']},
            format='json')
        force_authenticate(request, user=self.user)
        SewRelationViewSet.as_view({'post': 'rebutjar_proposta'})(request)

        claus = {tuple(x['clau']) for x in self._propostes().data['propostes']}
        self.assertNotIn(tuple(p['clau']), claus)

    # ── T3: llegir i DESFER els rebuigs (QA-TALLER F) ───────────────────────

    def _llista_rebuigs(self):
        request = self.factory.get(
            '/api/v1/patterns/sew-proposal-rejections/', {'model': self.model.id})
        force_authenticate(request, user=self.user)
        return SewProposalRejectionViewSet.as_view({'get': 'list'})(request)

    def _desfa_rebuig(self, rid):
        request = self.factory.delete(f'/api/v1/patterns/sew-proposal-rejections/{rid}/')
        force_authenticate(request, user=self.user)
        return SewProposalRejectionViewSet.as_view({'delete': 'destroy'})(request, pk=rid)

    def _claus(self):
        return {tuple(x['clau']) for x in self._propostes().data['propostes']}

    def test_el_rebuig_es_pot_llegir_amb_la_cara_que_tenia_a_la_pantalla(self):
        """Els ids dels trams no identifiquen res per a ningú: el que la persona va veure quan
        va dir que no era «TATE_BACK · 25,3 cm ⛓ TATE_FRONT · 25,2 cm»."""
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        self._rebutja(p, motiu='no es cusen')

        resp = self._llista_rebuigs()

        self.assertEqual(resp.status_code, 200)
        fila = resp.data['results'][0]
        self.assertEqual({fila['peca_a'], fila['peca_b']}, {'TATE_BACK', 'TATE_FRONT'})
        self.assertEqual(fila['motiu'], 'no es cusen')
        for k in ('longitud_a_cm', 'longitud_b_cm'):
            self.assertGreater(fila[k], 0, f'{k} ha de portar la xifra que es va veure')

    def test_desfer_un_rebuig_torna_a_deixar_proposar_la_parella(self):
        """Persistent no vol dir irreversible. Sense el DELETE, un «no» premut per error amaga
        aquella parella per sempre i l'única sortida seria tornar a pujar el patró.

        La parella s'identifica per la seva CLAU i no per les peces que uneix: el TATE proposa
        més d'una costura entre el davanter i l'esquena, i buscar-la pel nom de les peces
        trobaria una germana i el test passaria sense provar res.
        """
        p = self._parella(self._propostes().data['propostes'], 'TATE_BACK', 'TATE_FRONT')
        clau = tuple(p['clau'])
        self._rebutja(p)
        self.assertNotIn(clau, self._claus(),
                         'el rebuig no ha amagat la parella: el test no prova res')
        rid = self._llista_rebuigs().data['results'][0]['id']

        resp = self._desfa_rebuig(rid)

        self.assertEqual(resp.status_code, 204)
        self.assertEqual(SewProposalRejection.objects.count(), 0)
        self.assertIn(clau, self._claus(),
                      'desfet el rebuig, el motor ha de tornar a poder proposar la parella')

    def test_els_rebuigs_dun_altre_model_no_es_llisten(self):
        p = self._propostes().data['propostes'][0]
        self._rebutja(p)
        altre = Model.objects.create(
            codi_intern='QA-PAT-0002', codi_tenant='TST', any=2026, temporada='SS', sequencial=2)

        request = self.factory.get(
            '/api/v1/patterns/sew-proposal-rejections/', {'model': altre.id})
        force_authenticate(request, user=self.user)
        resp = SewProposalRejectionViewSet.as_view({'get': 'list'})(request)

        self.assertEqual(resp.data['results'], [])


# ═════════════════════════════════════════════════════════════════════════════
# A1 — DETECCIÓ DE PINCES: el detector (engine pur)
# ═════════════════════════════════════════════════════════════════════════════

def _vora(punts_xy, girs_idx):
    """Una vora tancada de prova: coordenades i quins vèrtexs són GIRS."""
    pts = tuple(
        PointData(x=x, y=y, kind=(PointKind.TURN if i in girs_idx else PointKind.CURVE))
        for i, (x, y) in enumerate(punts_xy)
    )
    return BoundaryData(role=LayerRole.CUT, layer='1', points=pts, closed=True)


def _detecta(boundary, piquets_t=()):
    """El detector sobre una vora de prova, amb tot el que necessita ja calculat."""
    pts = list(boundary.points)
    girs = [i for i, p in enumerate(pts) if p.kind is PointKind.TURN]
    llarg = longitud_vora(boundary)
    acumulats, _ = acumulats_vora(boundary)
    return detectar(pts, girs, llarg, piquets_t, acumulats,
                    piece_id=1, piece_nom='PROVA', vora=0)


def _quadrat_amb_v(apex_dx=10.0, apex_dy=-6.0, boca=20.0):
    """Un quadrat de 50×50 cm (200 cm de vora) amb una V a la vora de baix.

    El quadrat va en sentit CCW i l'interior queda A DALT de la vora de baix: una V amb el
    vèrtex a `y` NEGATIVA apunta cap a FORA, que és el que fa una pinça de vora (v. la
    capçalera d'`engine.dart_detection`).
    """
    ax = 200.0
    return _vora(
        [(0, 0), (ax, 0), (ax + apex_dx, apex_dy), (ax + boca, 0),
         (500, 0), (500, 500), (0, 500)],
        girs_idx={0, 1, 2, 3, 4, 5, 6},
    )


class DeteccioPincaTest(unittest.TestCase):
    """La signatura d'una pinça de vora. **Els tests que manen són els negatius.**"""

    def test_una_V_petita_i_simetrica_cap_enfora_es_una_pinca(self):
        candidats = _detecta(_quadrat_amb_v())

        self.assertEqual(len(candidats), 1)
        c = candidats[0]
        self.assertEqual((c.index_a, c.index_vertex, c.index_b), (1, 2, 3))
        self.assertAlmostEqual(c.boca_cm, 2.0, places=1)
        self.assertGreaterEqual(c.confianca, LLINDAR_PINCA)

    def test_la_tela_que_es_menja_es_la_suma_dels_dos_costats(self):
        """És el número que després sortirà restat a la costura que la conté (W4b)."""
        c = _detecta(_quadrat_amb_v())[0]

        self.assertAlmostEqual(c.intake_cm, c.costat_a_cm + c.costat_b_cm, places=2)

    # ── ELS NEGATIUS ────────────────────────────────────────────────────────
    def test_una_CANTONADA_no_es_una_pinca(self):
        """La mateixa FORMA que una pinça, però a l'escala de la peça.

        Aquest és el test que justifica tot el disseny: una cantonada i una pinça tenen les
        mateixes ràtios (boca/costats, fondària/boca) i cap criteri invariant d'escala les
        distingeix. El que les separa és la boca CONTRA LA VORA.
        """
        # La V, ×10: costats i fondària proporcionals, boca del 10% de la vora.
        candidats = _detecta(_quadrat_amb_v(apex_dx=100.0, apex_dy=-60.0, boca=200.0))

        self.assertEqual(candidats, [])

    def test_els_girs_dune_CORBA_no_son_una_pinca(self):
        """Tres girs gairebé alineats (la curvatura d'una sisa): fondària zero, cap V."""
        boundary = _vora(
            [(0, 0), (200, 0), (210, -0.2), (220, 0), (500, 0), (500, 500), (0, 500)],
            girs_idx={0, 1, 2, 3, 4, 5, 6},
        )

        self.assertEqual(_detecta(boundary), [])

    def test_una_V_amb_els_costats_MOLT_desiguals_no_tanca_plana(self):
        """Els dos costats es cusen l'un contra l'altre: si no fan el mateix, no és una pinça."""
        candidats = _detecta(_quadrat_amb_v(apex_dx=4.0, apex_dy=-6.0, boca=20.0))

        self.assertEqual(candidats, [])

    def test_una_OSCA_cap_a_DINS_no_es_una_pinca(self):
        """Una V cap a dins RETALLA tela: la vora es fa més curta i no hi ha res per cosir.

        Una pinça de vora és tela que SOBRA —per això la vora fa una V cap enfora— i és el que
        fa que el davanter del TATE tingui 2,34 cm més de contorn que l'esquena.
        """
        candidats = _detecta(_quadrat_amb_v(apex_dy=+6.0))

        self.assertEqual(candidats, [])

    # ── la confiança i la clau ──────────────────────────────────────────────
    def test_els_piquets_a_la_boca_apugen_la_confianca(self):
        """El piquet és la marca que el CAD posa perquè els dos extrems es TROBIN."""
        boundary = _quadrat_amb_v()
        acumulats, total = acumulats_vora(boundary)
        t_boca = (acumulats[1] / total, acumulats[3] / total)

        sense = _detecta(boundary)[0]
        amb = _detecta(boundary, piquets_t=t_boca)[0]

        self.assertEqual(sense.piquets_boca, 0)
        self.assertEqual(amb.piquets_boca, 2)
        self.assertGreater(amb.confianca, sense.confianca)

    def test_la_clau_dune_pinca_es_canonica(self):
        """Una V llegida a l'inrevés és la MATEIXA V: el rebuig no pot deixar-la tornar."""
        self.assertEqual(clau_pinca(9, 5, 2), clau_pinca(2, 5, 9))


class PincesProposadesAPITest(PatternsAPITestBase):
    """A1 pel camí de l'API, amb el TATE real: detectar, confirmar (gest de W4b), rebutjar."""

    #: Els vèrtexs de la pinça del banc de W4b, sobre la vora de cosit del davanter.
    PINCA_A, PINCA_VERTEX, PINCA_B = 69, 70, 71

    def setUp(self):
        super().setUp()
        self.fp = PatternFile.objects.get(
            pk=self._upload(TATE_DXF.read_bytes()).data['id'])
        self.front = self.fp.pieces.get(nom_block='TATE_FRONT')
        self.vora = (self.front.segments
                     .filter(origen=PatternSegment.ORIGEN_AUTO).first().vora)
        self.pf = list(self.front.points
                       .filter(mena='vertex', boundary_index=self.vora).order_by('ordre'))

    def _candidats(self):
        request = self.factory.get(
            '/api/v1/patterns/sew-relations/pinces-proposades/', {'model': self.model.id})
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'get': 'pinces_proposades'})(request)

    def _confirma(self, c):
        """Confirmar = el gest de W4b. **El mateix endpoint**, no un de nou."""
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/pinca/',
            {'model': self.model.id, 'point_a': c['point_a'],
             'point_vertex': c['point_vertex'], 'point_b': c['point_b'],
             'nom': 'Pinça 1', 'nom_a': 'Pinça 1 · A', 'nom_b': 'Pinça 1 · B'},
            format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'pinca'})(request)

    def _rebutja(self, c):
        request = self.factory.post(
            '/api/v1/patterns/sew-relations/rebutjar-pinca/',
            {'model': self.model.id, 'point_a': c['point_a'],
             'point_vertex': c['point_vertex'], 'point_b': c['point_b']},
            format='json')
        force_authenticate(request, user=self.user)
        return SewRelationViewSet.as_view({'post': 'rebutjar_pinca'})(request)

    def _la_del_banc(self, candidats):
        esperats = {self.pf[self.PINCA_A].id, self.pf[self.PINCA_B].id}
        for c in candidats:
            if ({c['point_a'], c['point_b']} == esperats
                    and c['point_vertex'] == self.pf[self.PINCA_VERTEX].id):
                return c
        return None

    # ── T1/T2: el detector, sobre el material ───────────────────────────────
    def test_el_motor_troba_la_pinca_REAL_del_TATE(self):
        """La del banc de W4b: costats 1,33 i 1,01 — les xifres exactes, no aproximades."""
        resp = self._candidats()

        self.assertEqual(resp.status_code, 200)
        c = self._la_del_banc(resp.data['candidats'])
        self.assertIsNotNone(c, 'la pinça real del TATE no s\'ha detectat')
        self.assertAlmostEqual(c['costat_a_cm'], 1.33, places=2)
        self.assertAlmostEqual(c['costat_b_cm'], 1.01, places=2)
        self.assertAlmostEqual(c['intake_cm'], 2.34, places=2)

    def test_el_motor_no_es_menja_les_cantonades_del_TATE(self):
        """10 peces, 130 girs, i NOMÉS les pinces de debò. El fals positiu és el vertader
        enemic: una llista plena de cantonades ensenya a no mirar-la."""
        resp = self._candidats()

        self.assertEqual(len(resp.data['candidats']), 2)   # les dues del davanter, simètriques
        self.assertEqual(resp.data['peces'], 10)
        self.assertTrue(all(c['peca'] == 'TATE_FRONT' for c in resp.data['candidats']))

    def test_detectar_NO_escriu_res(self):
        abans = (SewRelation.objects.count(), PatternSegment.objects.count())

        self._candidats()

        self.assertEqual(abans, (SewRelation.objects.count(), PatternSegment.objects.count()))

    # ── T3: confirmar = el gest de W4b, pel MATEIX camí ─────────────────────
    def test_confirmar_una_pinca_proposada_deixa_el_MATEIX_que_el_gest_manual(self):
        c = self._la_del_banc(self._candidats().data['candidats'])

        resp = self._confirma(c)

        self.assertEqual(resp.status_code, 201, resp.data)
        rel = SewRelation.objects.get(pk=resp.data['id'])
        self.assertEqual(rel.tipus, SewRelation.TIPUS_PINCA)
        self.assertTrue(resp.data['es_pinca'])
        costats = list(rel.segments_a.all()) + list(rel.segments_b.all())
        self.assertEqual(len(costats), 2)
        for seg in costats:
            self.assertEqual(seg.origen, PatternSegment.ORIGEN_DECLARAT)

    def test_el_descompte_es_IDENTIC_al_de_la_pinca_marcada_a_ma(self):
        """El banc de W4b, sencer: 1,33 + 1,01 = 2,34 cm de tela que la costura ja no cus."""
        c = self._la_del_banc(self._candidats().data['candidats'])
        self._confirma(c)

        estat = comprovar_costura(SewRelation.objects.get(tipus=SewRelation.TIPUS_PINCA))

        self.assertAlmostEqual(
            estat['longitud_a_cm'] + estat['longitud_b_cm'], 2.34, places=2)

    def test_una_pinca_JA_DECLARADA_no_es_torna_a_proposar(self):
        c = self._la_del_banc(self._candidats().data['candidats'])
        self._confirma(c)

        resp = self._candidats()

        self.assertIsNone(self._la_del_banc(resp.data['candidats']))
        self.assertEqual(resp.data['descartats']['ja_declarades'], 1)

    # ── T3: el rebuig ───────────────────────────────────────────────────────
    def test_un_rebuig_de_pinca_es_PERSISTENT(self):
        c = self._la_del_banc(self._candidats().data['candidats'])

        resp = self._rebutja(c)

        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(self._la_del_banc(self._candidats().data['candidats']))
        self.assertEqual(self._candidats().data['descartats']['rebutjades'], 1)

    def test_rebutjar_dues_vegades_no_duplica_el_rebuig(self):
        c = self._la_del_banc(self._candidats().data['candidats'])
        self._rebutja(c)

        resp = self._rebutja(c)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['ja_hi_era'])
        self.assertEqual(DartProposalRejection.objects.count(), 1)
