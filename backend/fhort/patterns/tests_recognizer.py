"""Tests of the piece recognizer (F4.1).

New file, run on its own — the law of proportional suites:

    FTT_TEST_DB=test_ftt_f41 venv/bin/python manage.py test \
        fhort.patterns.tests_recognizer --settings=fhort.settings_test --keepdb

What each class defends, in one sentence each:

1. **`DescriptorPortTest`** — the corpus and FTT compute the SAME vector. If this ever goes
   red, every neighbour in the system is silently wrong and nothing else would say so.
2. **`CascadeTest`** — N1 beats N2, N3 re-scores without ruling, N4 stays quiet.
3. **`NeverTouchesConfirmedTest`** — the recognizer cannot write a confirmed identity. Not
   "does not": *cannot*.
4. **`EndpointTest`** — the re-run is idempotent and is the same path as the import.
"""
import os
import sys
from types import SimpleNamespace

import numpy as np
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.patterns.models import PatternFile, PatternPiece, PatternPoint
from fhort.patterns.recognition import bank as B
from fhort.patterns.recognition import recognizer as R
from fhort.patterns.recognition.descriptor import (DESC_DIM, MM_PER_CM,
                                                   features_from_outline)
from fhort.patterns.recognition.ftt_geometry import features_of_piece
from fhort.patterns.recognition.service import UPDATE_FIELDS, recognize_pattern_file
from fhort.pom.management.commands.seed_pattern_piece_roles import sembra as sembra_rols
from fhort.pom.models import GarmentType, PatternPieceRole
from fhort.tasks.models import GarmentTypeItem

#: A plain rectangle, in millimetres, closed. Small enough to reason about by hand.
RECT_MM = [(0, 0), (200, 0), (200, 500), (0, 500)]


def _outline(pts_mm, n=None):
    return np.asarray(pts_mm, dtype=float) / MM_PER_CM


class _Base(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant F4.1'

    def setUp(self):
        super().setUp()
        sembra_rols(connection.schema_name)
        self.roles = {r.slug: r for r in PatternPieceRole.objects.all()}
        gt = GarmentType.objects.create(codi_client='QA', nom_client='QA', grup='QA')
        self.gti = GarmentTypeItem.objects.create(garment_type=gt, code='qa', name='QA')

    # ── fabricar geometria sense DXF ─────────────────────────────────────────
    def _file(self, nom='qa.dxf'):
        return PatternFile.objects.create(nom_fitxer=nom, garment_type_item=self.gti)

    def _piece(self, pf, nom_block, pts_mm, role_slug=None, face=''):
        piece = PatternPiece.objects.create(
            pattern_file=pf, nom_block=nom_block,
            contorns=[{'index': 0, 'role': 'cut', 'layer': '1', 'closed': True}],
            piece_role=self.roles[role_slug] if role_slug else None,
            face=face)
        PatternPoint.objects.bulk_create([
            PatternPoint(piece=piece, mena='vertex', boundary_index=0, ordre=i,
                         x=x, y=y, tipus='turn')
            for i, (x, y) in enumerate(pts_mm)
        ])
        return piece


class DescriptorPortTest(_Base):
    """🚨 The corpus and FTT must compute the SAME vector, or the bank is a lie.

    The corpus half of the bank was computed by `/root/gcd_corpus/scripts/descriptors.py`
    at ingest time — 1,4 M rows that are now data and cannot be recomputed cheaply. The FTT
    half is computed by `recognition/descriptor.py`. If the two ever disagree, every
    distance in the system is wrong and **nothing else in the suite would notice**: the
    query still returns neighbours, they are just the wrong ones.

    So this test feeds the SAME geometry to both and demands they agree. It compares
    against the shipping ingest code, not against a re-reading of the spec, because the
    database holds what that code produced.
    """

    CORPUS_SCRIPTS = '/root/gcd_corpus/scripts'

    def test_the_two_paths_give_the_same_vector(self):
        if not os.path.isdir(self.CORPUS_SCRIPTS):
            self.skipTest('corpus ingest scripts not on this machine')
        sys.path.insert(0, self.CORPUS_SCRIPTS)
        sys.path.insert(0, '/root/n2_gym/scripts')
        try:
            import descriptors as corpus
        except ImportError:
            self.skipTest('corpus descriptors module not importable')

        rng = np.random.default_rng(20260826)
        for k in range(5):
            # A closed convex-ish polygon in cm, the shape a panel outline has.
            ang = np.sort(rng.uniform(0, 2 * np.pi, 9))
            rad = rng.uniform(8.0, 40.0, 9)
            P = np.stack([rad * np.cos(ang), rad * np.sin(ang)], axis=1)

            mine = features_from_outline(P, n_edges=9, n_curved=3, mirror=(k % 2 == 1))
            Qc, elong, area = corpus.canonical_frame(
                corpus.resample_closed(P), (k % 2 == 1))
            per = float(np.linalg.norm(
                np.diff(np.vstack([Qc, Qc[:1]]), axis=0), axis=1).sum())
            theirs = corpus.descriptor(
                Qc, area, per,
                {'edges': [{'curvature': {'type': 'cubic'}}] * 3 + [{}] * 6})

            self.assertEqual(len(mine['descriptor']), DESC_DIM)
            np.testing.assert_array_equal(
                mine['descriptor'], theirs,
                err_msg='the FTT and corpus descriptors have drifted apart')
            np.testing.assert_array_equal(mine['contour_rs'], Qc.astype(np.float32))

    def test_millimetres_are_converted_and_the_conversion_matters(self):
        """A factor-of-ten slip does not degrade the match — it destroys it.

        Channels 0 and 1 are absolute scale in log units, so mistaking mm for cm shifts
        them by log(10) ≈ 2,30 each. This test exists so that mistake is loud.
        """
        cm = _outline(RECT_MM)
        a = features_from_outline(cm, 4, 0)
        b = features_from_outline(np.asarray(RECT_MM, dtype=float), 4, 0)
        # 20 x 50 cm = 1.000 cm². Surt 999,76, i el 0,02 % que falta NO és un error: el
        # contorn es remostreja a 128 punts equidistants en llargada d'arc, i les
        # cantonades d'un rectangle no cauen mai justes damunt d'una mostra, o sigui que
        # el polígon remostrejat les talla de gairell. És una propietat del descriptor i
        # afecta IGUAL els dos costats del banc, que és el que fa que no importi.
        self.assertAlmostEqual(a['area_cm2'], 1000.0, delta=0.5)
        self.assertAlmostEqual(
            float(b['descriptor'][0] - a['descriptor'][0]), 2 * np.log(MM_PER_CM),
            places=4)


class CascadeTest(_Base):
    """N1 beats N2 · N3 informs without ruling · N4 keeps quiet."""

    def _bank_of(self, *specs):
        pf = self._file('bank.dxf')
        for nom, pts, slug in specs:
            self._piece(pf, nom, pts, role_slug=slug)
        return pf, B.build_tenant_bank()

    def test_N1_wins_over_N2_when_the_geometry_is_the_same(self):
        """An identical piece is not "very similar": it is the same piece, and says so."""
        bank_pf, bank = self._bank_of(
            ('BANK_FRONT', RECT_MM, 'front'),
            ('BANK_SLEEVE', [(0, 0), (900, 0), (900, 300), (0, 300)], 'sleeve'))
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'NOU', RECT_MM)
        res = R.recognize_pieces([p], tenant_bank=bank, pair_index={})
        self.assertEqual(res[p.pk]['ftt_slug'], 'front')
        self.assertEqual(res[p.pk]['evidence']['stage'], 'N1')
        self.assertEqual(res[p.pk]['score'], 1.0)

    def test_N2_proposes_on_a_similar_but_not_identical_piece(self):
        bank_pf, bank = self._bank_of(
            ('BANK_FRONT', RECT_MM, 'front'),
            ('BANK_CUFF', [(0, 0), (400, 0), (400, 40), (0, 40)], 'cuff'))
        pf = self._file('nou.dxf')
        # 2 % bigger: unmistakably the same family, unmistakably not the same piece.
        p = self._piece(pf, 'NOU', [(x * 1.02, y * 1.02) for x, y in RECT_MM])
        res = R.recognize_pieces([p], tenant_bank=bank, pair_index={})
        self.assertEqual(res[p.pk]['ftt_slug'], 'front')
        self.assertEqual(res[p.pk]['evidence']['stage'], 'N2')
        self.assertLess(res[p.pk]['score'], 1.0)

    def test_N4_stays_silent_when_nothing_is_close(self):
        """🚨 The load-bearing test of the whole sprint.

        The recognizer is allowed to be useless. It is not allowed to be confidently
        wrong. A shape the bank has never seen must come back with `ftt_slug=None` and an
        evidence blob that says why — not with the nearest of two bad options.
        """
        bank_pf, bank = self._bank_of(
            ('BANK_FRONT', RECT_MM, 'front'),
            ('BANK_BACK', [(0, 0), (210, 0), (210, 505), (0, 505)], 'back'))
        pf = self._file('nou.dxf')
        # Two near-identical rectangles in the bank ⇒ any rectangle is a coin flip
        # between them, and a coin flip is exactly what must not be shown as an answer.
        p = self._piece(pf, 'NOU', [(0, 0), (205, 0), (205, 502), (0, 502)])
        res = R.recognize_pieces([p], tenant_bank=bank, pair_index={})
        self.assertIsNone(res[p.pk]['ftt_slug'])
        self.assertEqual(res[p.pk]['evidence']['stage'], 'N4')
        self.assertIn('below the threshold', res[p.pk]['evidence']['silent_because'])

    def test_N3_re_scores_but_cannot_rule(self):
        """Graph support may lift a score; it may never carry one over the line alone."""
        bank_pf, bank = self._bank_of(
            ('BANK_FRONT', RECT_MM, 'front'),
            ('BANK_CUFF', [(0, 0), (400, 0), (400, 40), (0, 40)], 'cuff'))
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'NOU', [(x * 1.02, y * 1.02) for x, y in RECT_MM])

        sense = R.recognize_pieces([p], tenant_bank=bank, pair_index={})
        amb = R.recognize_pieces([p], tenant_bank=bank,
                                 pair_index={('back', 'front'): 3})
        # No other confident piece in this pattern ⇒ nothing to be sewn to ⇒ no boost.
        self.assertEqual(sense[p.pk]['score'], amb[p.pk]['score'])
        self.assertEqual(sense[p.pk]['evidence']['context']['boost'], 0.0)
        # And the ceiling is a constant, not a judgement call.
        self.assertLessEqual(R.N3_MAX_BOOST, 0.10)

    def test_the_silence_still_carries_its_evidence(self):
        """«I looked and I do not know» is an answer, and it has to be explainable."""
        bank_pf, bank = self._bank_of(
            ('BANK_FRONT', RECT_MM, 'front'),
            ('BANK_BACK', [(0, 0), (210, 0), (210, 505), (0, 505)], 'back'))
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'NOU', [(0, 0), (205, 0), (205, 502), (0, 502)])
        ev = R.recognize_pieces([p], tenant_bank=bank, pair_index={})[p.pk]['evidence']
        self.assertGreater(ev['n_neighbours'], 0)
        self.assertIn('nearest', ev)
        self.assertIn('geometry', ev)
        self.assertEqual(ev['threshold'], R.SCORE_MIN)


class NeverTouchesConfirmedTest(_Base):
    """🚨 The guarantee the whole screen rests on: the green is the human's.

    Not "the recognizer is careful not to write `piece_role`" — it *cannot*, because
    `service.UPDATE_FIELDS` is what reaches the database and the confirmed columns are not
    on it. This test asserts the list itself, so the guarantee survives somebody adding a
    field in a hurry six months from now.
    """

    FORBIDDEN = {'piece_role', 'face', 'rol', 'rol_origen', 'nom', 'lateralitat'}

    def test_update_fields_cannot_reach_a_confirmed_column(self):
        self.assertEqual(self.FORBIDDEN & set(UPDATE_FIELDS), set())
        self.assertEqual(set(UPDATE_FIELDS), {
            'proposed_role', 'proposed_face', 'proposed_score',
            'proposed_evidence', 'proposed_at'})

    def test_running_the_recognizer_leaves_a_confirmed_piece_untouched(self):
        bank_pf = self._file('bank.dxf')
        self._piece(bank_pf, 'BANK_FRONT', RECT_MM, role_slug='front')
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'JA_CONFIRMADA', RECT_MM, role_slug='back', face='back')
        p.rol_origen = PatternPiece.ROL_ORIGEN_CONFIRMAT
        p.nom = 'el bateig del taller'
        p.save(update_fields=['rol_origen', 'nom'])

        recognize_pattern_file(pf)
        p.refresh_from_db()
        # The proposal disagrees with the human — and the human wins, in silence.
        self.assertEqual(p.piece_role.slug, 'back')
        self.assertEqual(p.face, 'back')
        self.assertEqual(p.rol_origen, PatternPiece.ROL_ORIGEN_CONFIRMAT)
        self.assertEqual(p.nom, 'el bateig del taller')
        self.assertEqual(p.proposed_role.slug, 'front')

    def test_the_proposal_survives_confirmation_so_accuracy_stays_measurable(self):
        bank_pf = self._file('bank.dxf')
        self._piece(bank_pf, 'BANK_FRONT', RECT_MM, role_slug='front')
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'NOU', RECT_MM)
        recognize_pattern_file(pf)
        p.refresh_from_db()
        self.assertEqual(p.proposed_role.slug, 'front')

        from fhort.patterns.services import identificar_peces
        identificar_peces(pattern_file=pf,
                          files=[{'piece_id': p.pk,
                                  'piece_role_id': self.roles['front'].pk}])
        p.refresh_from_db()
        self.assertEqual(p.piece_role.slug, 'front')
        # …and the proposal is STILL there. Without this, "how often was it right?" is
        # unanswerable the moment anybody confirms anything.
        self.assertEqual(p.proposed_role.slug, 'front')
        self.assertIsNotNone(p.proposed_score)


class EndpointTest(_Base):
    """The re-run button and the import hook are the same path, and it is idempotent."""

    def setUp(self):
        super().setUp()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('qa41', password='x')
        # 🚨 `HTTP_HOST` amb el domini del tenant, i no és un detall del test: sense
        # això la petició resol el schema PÚBLIC, on `patterns` ni tan sols té ruta —dona
        # 404— **i deixa la connexió apuntant a public**, o sigui que el test següent peta
        # amb `relation "tasks_garmenttypeitem" does not exist`. Un símptoma a dues
        # passes, i la causa és una sola línia.
        self.client = APIClient(HTTP_HOST=self.get_test_tenant_domain())
        self.client.force_authenticate(self.user)

    def test_recognize_is_idempotent(self):
        bank_pf = self._file('bank.dxf')
        self._piece(bank_pf, 'BANK_FRONT', RECT_MM, role_slug='front')
        pf = self._file('nou.dxf')
        p = self._piece(pf, 'NOU', RECT_MM)

        url = '/api/v1/patterns/pattern-files/{}/recognize/'.format(pf.pk)
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 200, r1.content[:400])
        p.refresh_from_db()
        first = (p.proposed_role_id, p.proposed_score, p.proposed_evidence['stage'])

        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(
            (p.proposed_role_id, p.proposed_score, p.proposed_evidence['stage']), first)
        self.assertEqual(r1.data['pieces'], r2.data['pieces'])

    def test_the_proposal_reaches_the_api_with_its_evidence(self):
        """The UI cannot paint a reason it was never given."""
        bank_pf = self._file('bank.dxf')
        self._piece(bank_pf, 'BANK_FRONT', RECT_MM, role_slug='front')
        pf = self._file('nou.dxf')
        self._piece(pf, 'NOU', RECT_MM)
        self.client.post('/api/v1/patterns/pattern-files/{}/recognize/'.format(pf.pk))

        r = self.client.get('/api/v1/patterns/pattern-files/{}/'.format(pf.pk))
        self.assertEqual(r.status_code, 200)
        peca = [x for x in r.data['pieces'] if x['nom_block'] == 'NOU'][0]
        self.assertEqual(peca['proposta']['role']['slug'], 'front')
        self.assertFalse(peca['proposta']['is_confirmed'])
        self.assertIn('nearest', peca['proposta']['evidence'])
