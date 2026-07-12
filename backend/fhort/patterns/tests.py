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
)
from fhort.patterns.engine.geometry import (
    Confidence,
    GradeRuleData,
    LayerRole,
    POMAnchorData,
    PointKind,
    UnitsMethod,
)
from fhort.patterns.engine.roundtrip import compare, compare_grade_tables
from fhort.patterns.engine.rul_reader import RULReader, coherencia_dxf_rul
from fhort.patterns.engine.rul_writer import RULWriter

# ── el que només fa falta per als tests de S3 (adaptadors: SÍ que toquen Django) ──
import datetime
import time
from unittest import mock
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import Model
from fhort.models_app.services_fitxers import DOWNLOAD_SALT as MODEL_FITXER_SALT
from fhort.patterns.adapters import DjangoGeometryStore
from fhort.patterns.models import PatternFile
from fhort.patterns.services import save_pattern_file
from fhort.patterns.views import (PATTERN_DOWNLOAD_SALT, PATTERN_RUL_DOWNLOAD_SALT,
                                  PatternFileViewSet)
from fhort.pom.models import GarmentType
from fhort.tasks.models import GarmentTypeItem

FIXTURES = Path(__file__).parent / 'tests' / 'fixtures'
AMELIA_DXF = FIXTURES / 'AMELIA_AZUL_prova.dxf'
AMELIA_RUL = FIXTURES / 'AMELIA_AZUL_prova.rul'

#: El material és el contracte. Si algú el toca, els recomptes de sota deixen de
#: voler dir res i val més que el test ho canti que no pas que passi en silenci.
AMELIA_DXF_MD5 = '2ae0006e003ebe17326187d79bb587d5'


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
            'FTT POM-001 CHEST WIDTH = 525.0 mm',
        )

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
