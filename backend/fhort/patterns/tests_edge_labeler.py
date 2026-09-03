"""Tests of the edge-role grammar and the derived landmarks (F4.2).

New file, run on its own — the law of proportional suites:

    FTT_TEST_DB=test_ftt_f42 venv/bin/python manage.py test \
        fhort.patterns.tests_edge_labeler --settings=fhort.settings_test --keepdb

What each class defends, in one sentence:

1. **`FrameTest`** — the frame comes from the grain, and a piece read a quarter turn round
   is read the same. This is the one that would catch the finding that made F4.2 possible.
2. **`GrammarTest`** — a clean cycle gets named, an unreadable one stays quiet, and the
   silence is per EDGE.
3. **`DInv8Test`** — the shoulder is found by STRUCTURE even where shape says little.
4. **`LandmarkTest`** — the HPS resolves, the `highest_y` verifier goes RED when the piece
   is fed in the wrong frame, and a piece with two sides yields two of everything.
5. **`VocabularyTest`** — `needs_piece_role` filters the selector, and confirmation cannot
   be talked into an impossible role.
6. **`NeverTouchesGeometryTest`** — confirming a name writes the NAME and nothing else.

🚨 Every synthetic piece here is at REAL SCALE, in millimetres. A 4×4 unit square would
pass rules that are all ratios and prove nothing about a garment; a 600 mm hem under a
780 mm shoulder is a bodice, and the numbers have to behave like one.
"""
import math

from django.db import connection
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from fhort.patterns.landmark_service import derive_landmarks
from fhort.patterns.models import PatternFile, PatternPiece, PatternPoint, PatternSegment
from fhort.patterns.recognition.edge_frame import NoFrame, frame_of_grain
from fhort.patterns.recognition.edge_labeler import RawEdge, label_piece
from fhort.patterns.recognition.edge_service import (UPDATE_FIELDS,
                                                     EdgeConfirmationRejected,
                                                     confirm_edge_roles, edge_vocabulary,
                                                     propose_edge_roles)
from fhort.pom.landmarks import LandmarkNoResolt, Tram, resol_landmark
from fhort.pom.management.commands.seed_pattern_piece_roles import sembra as sembra_rols
from fhort.pom.models import (EdgeRole, GarmentType, GarmentTypeItemEdgeProfile,
                              LandmarkRole, PatternPieceRole, SeamPairTemplate)
from fhort.tasks.models import GarmentTypeItem


def _arc(a, b, bulge, n=9):
    """A gentle arc from `a` to `b`, bulging sideways. Curvature the rules can read.

    An armhole that comes out perfectly straight is not an armhole, and the grammar leans
    on exactly that: a synthetic cycle whose curves are polylines of two points would test
    a garment nobody cuts.
    """
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    out = []
    for i in range(n + 1):
        t = i / n
        s = math.sin(math.pi * t) * bulge
        out.append((ax + dx * t - dy / math.hypot(dx, dy) * s,
                    ay + dy * t + dx / math.hypot(dx, dy) * s))
    return out


#: A bodice front at real scale, in millimetres, garment vertical along +Y and symmetric
#: about x = 0. Hem 600 mm wide, shoulders at 780 mm — a real size-M front, not a token.
def bodice_front(rot=0.0, dx=0.0, dy=0.0):
    """The cycle and the grain line, optionally rotated on the sheet.

    The rotation is the point of the fixture: on this house's material NO piece lies with
    its grain vertical, and a grammar that only works at rot=0 would have passed every test
    while being wrong on every real file.
    """
    # 🚨 The armhole bulge is 40 mm and not a token amount: it puts the arc's straightness
    # at 0,885, against the 0,901 the 837's own armhole measures. The grammar tells an
    # armhole from a side seam BY CURVATURE, so a shallow synthetic arc would be testing a
    # garment nobody cuts — the first run of this fixture used 18 mm, read 0,972, and the
    # labeller called it a side seam. It was right to.
    edges = [
        [(-300, 0), (300, 0)],                                    # hem
        [(300, 0), (250, 600)],                                   # side seam R
        _arc((250, 600), (180, 750), 40),                         # armhole R
        [(180, 750), (120, 780)],                                 # shoulder R
        _arc((120, 780), (-120, 780), -55),                       # neckline, crosses axis
        [(-120, 780), (-180, 750)],                               # shoulder L
        _arc((-180, 750), (-250, 600), 40),                       # armhole L
        [(-250, 600), (-300, 0)],                                 # side seam L
    ]
    grain = {'x1': 0.0, 'y1': 100.0, 'x2': 0.0, 'y2': 500.0}

    c, s = math.cos(rot), math.sin(rot)

    def T(p):
        return (p[0] * c - p[1] * s + dx, p[0] * s + p[1] * c + dy)

    edges = [[T(p) for p in e] for e in edges]
    g1, g2 = T((grain['x1'], grain['y1'])), T((grain['x2'], grain['y2']))
    return edges, {'x1': g1[0], 'y1': g1[1], 'x2': g2[0], 'y2': g2[1]}


FRONT_TRUTH = ['hem', 'side_seam', 'armhole', 'shoulder_seam', 'neckline',
               'shoulder_seam', 'armhole', 'side_seam']

FRONT_VOCAB = ('hem', 'side_seam', 'armhole', 'shoulder_seam', 'neckline',
               'centre_front', 'waistline')


def _labels(edges, grain, vocab=FRONT_VOCAB, role='front', **kw):
    out = label_piece([RawEdge(points=e) for e in edges], grain, role,
                      vocabulary=vocab, **kw)
    return [p.edge_role for p in out['proposals']], out


class FrameTest(SimpleTestCase):
    """🚨 The frame is the finding. Everything else in F4.2 stands on it."""

    def test_a_grain_line_gives_the_axis(self):
        f = frame_of_grain({'x1': 10.0, 'y1': 20.0, 'x2': 10.0, 'y2': 120.0})
        u, v = f.to_frame(10.0, 70.0)
        self.assertAlmostEqual(u, 50.0)
        self.assertAlmostEqual(v, 0.0, places=9)

    def test_no_grain_is_a_silence_with_a_reason(self):
        for bad in (None, {}, {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}):
            with self.assertRaises(NoFrame):
                frame_of_grain(bad)

    def test_the_same_piece_reads_the_same_however_it_lies_on_the_sheet(self):
        """The measured reality: 60 of 60 pieces in the tenant lie turned, none upright.

        A grammar calibrated on sheet coordinates would read this fixture perfectly at
        rot=0 and be 90° wrong on every file the workshop actually owns.
        """
        base, _ = _labels(*bodice_front())
        self.assertEqual(base, FRONT_TRUTH)
        for rot in (math.pi / 2, -math.pi / 2, math.pi, 0.7):
            got, _ = _labels(*bodice_front(rot=rot, dx=1500, dy=-800))
            self.assertEqual(got, FRONT_TRUTH, 'rotated by {:.2f} rad'.format(rot))

    def test_the_orientation_is_decided_and_recorded(self):
        _, out = _labels(*bodice_front())
        self.assertGreater(out['orientation']['lead'], 0.05)


class GrammarTest(SimpleTestCase):

    def test_a_clean_cycle_gets_every_edge_named(self):
        got, out = _labels(*bodice_front())
        self.assertEqual(got, FRONT_TRUTH)
        self.assertTrue(all(p.score > 0 for p in out['proposals']))

    def test_an_empty_vocabulary_is_silence_and_says_so(self):
        """A placket has no row in either catalogue table. The right answer is nothing.

        Measured on the 837: `TAPETA` is silent on all four of its edges, and the reason is
        the catalogue's, not the labeller's.
        """
        got, out = _labels(*bodice_front(), vocab=(), role='placket')
        self.assertEqual(got, [None] * 8)
        self.assertIn('placket', out['silent_because'])

    def test_silence_is_per_edge_and_the_confident_ones_still_speak(self):
        """🚨 N4. A front whose hem and sides are obvious does not go quiet as a whole.

        Driven by raising the threshold rather than by deforming the piece: the same cycle,
        a stricter bar, and what survives must be exactly the edges with the widest margins
        — never zero of them, never all of them.
        """
        got, out = _labels(*bodice_front(), threshold=0.65)
        self.assertIn(None, got)
        self.assertTrue(any(g is not None for g in got))
        for p in out['proposals']:
            if p.edge_role is None and p.evidence.get('scores'):
                self.assertIn('threshold', p.evidence['why'])

    def test_an_edge_that_no_rule_scores_says_which_words_had_no_rule(self):
        got, out = _labels(*bodice_front(), vocab=('gore_seam', 'crotch_seam'))
        self.assertEqual(got, [None] * 8)
        self.assertIn('gore_seam', out['proposals'][0].evidence['unruled_roles'])


class DInv8Test(SimpleTestCase):
    """🚨 D-INV-8 is a RULE, not a vote: the shoulder is the ONE edge between the two.

    Structural and not lucky — the neckline and the armhole are cut at two disjoint corners
    of the same panel and exactly one edge lies between them, measured 2 371 of 2 371
    (`LandmarkRole.hps`). So where it applies it overrules shape, and it has to be visible
    in the evidence that it did.
    """

    def test_the_shoulder_is_named_by_structure_and_the_evidence_says_so(self):
        _, out = _labels(*bodice_front())
        shoulders = [p for p in out['proposals'] if p.edge_role == 'shoulder_seam']
        self.assertEqual(len(shoulders), 2)
        self.assertTrue(any('D-INV-8' in p.evidence['why'] for p in shoulders),
                        'no shoulder was reached by the structural rule')

    def test_without_a_neckline_or_an_armhole_the_rule_stands_down(self):
        """It fires on the shape it describes and on nothing else.

        With `armhole` out of the vocabulary there is no gap for the rule to measure, and
        it must not fall back to picking whichever edge looks most shoulder-ish: a rule
        that fires when its premise is absent is not a rule.
        """
        _, out = _labels(*bodice_front(),
                         vocab=('hem', 'side_seam', 'shoulder_seam', 'neckline'))
        self.assertFalse(any('D-INV-8' in p.evidence['why'] for p in out['proposals']))

    def test_a_short_fragment_between_two_agreeing_edges_is_bridged(self):
        """The 837 carries four 17 mm jogs mid side-seam. The first exam called them hems.

        Structure over shape, same family as D-INV-8: where a 17 mm step's own geometry
        says nothing, what surrounds it says everything.
        """
        edges, grain = bodice_front()
        # Split one side seam into two with a tiny jog between, as a seam allowance step.
        # Shaped like the 837's own: ~17 mm ACROSS the body, ~1 mm along it. A jog that
        # ran ALONG the seam would still read as side seam on its own and would prove
        # nothing; it is the across-the-body step whose geometry says nothing.
        edges[1:2] = [[(300, 0), (280, 300)], [(280, 300), (297, 299)],
                      [(297, 299), (250, 600)]]
        got, out = _labels(edges, grain)
        self.assertEqual(got[1:4], ['side_seam', 'side_seam', 'side_seam'])
        self.assertIn('fragment', out['proposals'][2].evidence['why'])


class LandmarkTest(SimpleTestCase):
    """The pure resolver, and the frame it has to be fed in."""

    HPS = type('R', (), {'derivable': True, 'derivation_op': 'shared_endpoint',
                         'derivation_input': {'a': 'neckline', 'b': 'shoulder_seam'},
                         'derivation_tiebreak': 'highest_y', 'slug': 'hps'})()

    def test_the_hps_is_where_the_neckline_meets_the_shoulder(self):
        graph = [Tram('neckline', (0, 780), (120, 780)),
                 Tram('shoulder_seam', (120, 780), (180, 750)),
                 Tram('armhole', (180, 750), (250, 600))]
        self.assertEqual(resol_landmark(self.HPS, graph), (120, 780))

    def test_the_highest_y_verifier_goes_red_when_the_frame_is_wrong(self):
        """🚨 THE MEASUREMENT THAT MADE `landmark_service` NECESSARY.

        The same three edges, read in SHEET coordinates for a piece that lies a quarter
        turn round: the shared endpoint is unchanged and correct, and `highest_y` rejects it
        — because in that frame it is not the highest, and the verifier is right to say so.
        The bug was never the verifier; it was the coordinates it was shown.
        """
        turned = [Tram('neckline', (780, 0), (780, -120)),
                  Tram('shoulder_seam', (780, -120), (750, -180)),
                  Tram('armhole', (750, -180), (600, -250))]
        with self.assertRaises(LandmarkNoResolt) as ctx:
            resol_landmark(self.HPS, turned)
        self.assertIn('highest_y', str(ctx.exception))

    def test_two_shoulders_and_one_neckline_share_two_endpoints_not_one(self):
        """Why `landmark_service` resolves per SIDE, and why refusing here is correct.

        A front cut in one flat piece has two HPS. `_shared_endpoint` demands exactly one
        shared endpoint and must NOT quietly pick either — the whole-cycle graph is the
        wrong question, not a hard one.
        """
        both = [Tram('neckline', (-120, 780), (120, 780)),
                Tram('shoulder_seam', (120, 780), (180, 750)),
                Tram('shoulder_seam', (-120, 780), (-180, 750))]
        with self.assertRaises(LandmarkNoResolt) as ctx:
            resol_landmark(self.HPS, both)
        self.assertIn('2 extrems', str(ctx.exception))


class _DbBase(TenantTestCase):
    """A tenant with the piece-role catalogue and just enough of the semantic one.

    The edge catalogue is seeded HERE, by hand and small, rather than by running the F3
    seeder: the rows this suite reasons about have to be visible in the test that reasons
    about them, or a change to the seeder would move a test's meaning without touching it.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant F4.2'
        tenant.paid_until = '2100-01-01'
        tenant.on_trial = False

    def setUp(self):
        super().setUp()
        sembra_rols(connection.schema_name)
        self.roles = {r.slug: r for r in PatternPieceRole.objects.all()}
        for i, (slug, zone, kind, mates, needs) in enumerate([
                ('neckline', 'neck', 'opening', 'collar_attach', False),
                ('collar_attach', 'neck', 'seam', 'neckline', False),
                ('shoulder_seam', 'shoulder', 'seam', 'shoulder_seam', False),
                ('armhole', 'arm', 'opening', 'sleeve_cap', False),
                ('side_seam', 'torso', 'seam', 'side_seam', True),
                ('centre_front', 'torso', 'seam', 'centre_front', True),
                ('hem', 'any', 'finished', '', True),
                ('inseam', 'leg', 'seam', 'inseam', True),
                ('crotch_seam', 'leg', 'seam', 'crotch_seam', False)]):
            EdgeRole.objects.create(
                slug=slug, nom_en=slug, nom_ca=slug, nom_es=slug, zone=zone, kind=kind,
                mates_slug=mates, needs_piece_role=needs, display_order=i, is_system=True)
        for kind, a, b in [
                ('union', ('collar', 'front', 'collar_attach'), ('front', 'front', 'neckline')),
                ('union', ('front', 'front', 'shoulder_seam'), ('back', 'back', 'shoulder_seam')),
                ('union', ('front', 'front', 'side_seam'), ('back', 'back', 'side_seam')),
                ('union', ('front', 'front', 'armhole'), ('sleeve', 'front', 'sleeve_cap')),
                ('centre', ('front', 'front', 'centre_front'), ('front', 'front', 'centre_front')),
                ('union', ('pant', 'front', 'inseam'), ('pant', 'back', 'inseam'))]:
            SeamPairTemplate.objects.create(
                seam_kind=kind, piece_role_a_slug=a[0], face_a=a[1], edge_role_a_slug=a[2],
                piece_role_b_slug=b[0], face_b=b[1], edge_role_b_slug=b[2], is_system=True)
        LandmarkRole.objects.create(
            slug='hps', nom_en='HPS', nom_ca='HPS', nom_es='HPS', zone='shoulder',
            derivable=True, derivation_op='shared_endpoint', derivation_tiebreak='highest_y',
            derivation_input={'a': 'neckline', 'b': 'shoulder_seam'}, is_system=True)
        # `patternfile_xor_model_item`: a PatternFile hangs off exactly one owner.
        gt = GarmentType.objects.create(codi_client='QA', nom_client='QA', grup='QA')
        self.gti = GarmentTypeItem.objects.create(garment_type=gt, code='qa42', name='QA')
        # 🚨 The FINISHED edges live ONLY here, and the first run of this suite proved why
        # by refusing `hem` on a front: a hem is sewn to nothing, so it appears in no seam
        # pair, and a fixture that seeds only `SeamPairTemplate` has no word for it. That
        # refusal was the vocabulary guard working; the fixture was the thing missing data.
        for rol, vora in (('front', 'hem'), ('back', 'hem'),
                          ('front', 'centre_front'), ('collar', 'collar_attach')):
            GarmentTypeItemEdgeProfile.objects.create(
                garment_type_item=self.gti, piece_role_slug=rol, edge_role_slug=vora,
                presence=GarmentTypeItemEdgeProfile.PRESENCE_CORE, is_system=True)

    def _front(self, rot=0.0):
        """A real front in the database: points, natural segments, grain, confirmed role."""
        edges, grain = bodice_front(rot=rot, dx=2000, dy=1200)
        pf = PatternFile.objects.create(nom_fitxer='qa-f42.dxf',
                                        garment_type_item=self.gti)
        piece = PatternPiece.objects.create(
            pattern_file=pf, nom_block='QA_FRONT', grain=grain,
            contorns=[{'index': 0, 'role': 'cut', 'layer': '1', 'closed': True}],
            piece_role=self.roles['front'], face='front',
            rol_origen=PatternPiece.ROL_ORIGEN_ASSIGNAT)

        # The outline as one ring of vertices, and the segments as spans over it — exactly
        # the shape `engine.segments` persists, so `edges_of_piece` is exercised for real
        # rather than bypassed.
        ring, spans = [], []
        for e in edges:
            spans.append(len(ring))
            ring.extend(e[:-1])
        PatternPoint.objects.bulk_create([
            PatternPoint(piece=piece, mena='vertex', boundary_index=0, ordre=i,
                         x=x, y=y, tipus='turn')
            for i, (x, y) in enumerate(ring)])
        cum = [0.0]
        for a, b in zip(ring, ring[1:] + ring[:1]):
            cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        total = cum[-1]
        segs = []
        for k, start in enumerate(spans):
            end = spans[k + 1] if k + 1 < len(spans) else 0
            segs.append(PatternSegment.objects.create(
                piece=piece, vora=0, origen=PatternSegment.ORIGEN_NATURAL,
                t_inici=cum[start] / total, t_fi=cum[end] / total, nom='tram {}'.format(k)))
        return pf, piece, segs


class VocabularyTest(_DbBase):
    """🚨 D3 · a role impossible for this piece cannot be proposed OR chosen by hand."""

    def test_the_vocabulary_only_holds_what_the_catalogue_pairs_with_this_role(self):
        vocab = edge_vocabulary('front')
        for expected in ('shoulder_seam', 'side_seam', 'armhole', 'centre_front'):
            self.assertIn(expected, vocab)
        # `inseam` and `crotch_seam` are legs. Nothing in the catalogue puts them on a
        # front, and `needs_piece_role` is exactly the flag that says so out loud.
        for impossible in ('inseam', 'crotch_seam'):
            self.assertNotIn(impossible, vocab)

    def test_a_role_with_no_catalogue_row_gets_no_words(self):
        self.assertEqual(edge_vocabulary('placket'), [])

    def test_the_proposer_never_leaves_the_vocabulary(self):
        _pf, piece, _segs = self._front()
        res = propose_edge_roles(piece)
        allowed = set(res['vocabulary'])
        for p in res['proposals']:
            if p['edge_role']:
                self.assertIn(p['edge_role'], allowed)

    def test_confirming_an_impossible_role_is_refused_with_the_reason(self):
        _pf, piece, segs = self._front()
        with self.assertRaises(EdgeConfirmationRejected) as ctx:
            confirm_edge_roles(
                piece=piece, rows=[{'segment_id': segs[0].pk, 'edge_role_slug': 'inseam'}])
        self.assertIn('front', str(ctx.exception))
        segs[0].refresh_from_db()
        self.assertIsNone(segs[0].edge_role_id)

    def test_a_piece_with_no_human_confirmed_role_is_not_asked(self):
        """Edges are named under a signed identity, never under a machine's proposal."""
        _pf, piece, _segs = self._front()
        piece.rol_origen = PatternPiece.ROL_ORIGEN_LLEGIT
        piece.save(update_fields=['rol_origen'])
        res = propose_edge_roles(piece)
        self.assertIsNone(res['piece_role'])
        self.assertEqual(res['proposals'], [])


class NeverTouchesGeometryTest(_DbBase):
    """🚨 Naming an edge is not permission to move it."""

    def test_update_fields_is_exactly_the_edge_role(self):
        self.assertEqual(UPDATE_FIELDS, ['edge_role'])

    def test_confirming_writes_the_name_and_leaves_the_span_alone(self):
        _pf, piece, segs = self._front()
        before = [(s.pk, s.t_inici, s.t_fi, s.nom, s.origen, s.vora) for s in segs]
        confirm_edge_roles(piece=piece, rows=[
            {'segment_id': segs[0].pk, 'edge_role_slug': 'hem'},
            {'segment_id': segs[1].pk, 'edge_role_slug': 'side_seam'}])
        for pk, t0, t1, nom, origen, vora in before:
            s = PatternSegment.objects.get(pk=pk)
            self.assertEqual((s.t_inici, s.t_fi, s.nom, s.origen, s.vora),
                             (t0, t1, nom, origen, vora))
        self.assertEqual(PatternSegment.objects.get(pk=segs[0].pk).edge_role.slug, 'hem')

    def test_clearing_a_role_is_allowed_and_is_not_a_deletion(self):
        _pf, piece, segs = self._front()
        confirm_edge_roles(piece=piece, rows=[
            {'segment_id': segs[0].pk, 'edge_role_slug': 'hem'}])
        confirm_edge_roles(piece=piece, rows=[
            {'segment_id': segs[0].pk, 'edge_role_slug': None}])
        s = PatternSegment.objects.get(pk=segs[0].pk)
        self.assertIsNone(s.edge_role_id)
        self.assertEqual(s.nom, 'tram 0')

    def test_a_segment_of_another_piece_is_refused(self):
        _pf, piece, segs = self._front()
        _pf2, _piece2, segs2 = self._front()
        with self.assertRaises(EdgeConfirmationRejected):
            confirm_edge_roles(
                piece=piece, rows=[{'segment_id': segs2[0].pk, 'edge_role_slug': 'hem'}])


class DerivedLandmarkDbTest(_DbBase):
    """The end of A11, on a piece that lives in the database and lies turned."""

    def test_a_turned_front_still_yields_two_hps(self):
        """🚨 The frame and the two sides, together, on the material's real geometry.

        Turned a quarter round on the sheet, because that is how every piece in the tenant
        lies. In sheet coordinates the `highest_y` verifier would reject both of these.
        """
        _pf, piece, _segs = self._front(rot=math.pi / 2)
        res = propose_edge_roles(piece)
        roles = {p['segment_id']: p['edge_role'] for p in res['proposals'] if p['edge_role']}
        out = derive_landmarks(piece, roles=roles)
        hps = [lm for lm in out['landmarks'] if lm['landmark'] == 'hps']
        self.assertEqual(len(hps), 2, out['skipped'])
        self.assertEqual({lm['side'] for lm in hps}, {'L', 'R'})

    def test_without_confirmed_edges_there_is_no_landmark_and_there_is_a_reason(self):
        _pf, piece, _segs = self._front()
        out = derive_landmarks(piece)
        self.assertEqual(out['landmarks'], [])
        self.assertTrue(any('confirmed role' in s['why'] for s in out['skipped']))
