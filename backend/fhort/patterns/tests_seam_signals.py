"""Tests dels dos senyals nous del motor de costures (F4.3).

Fitxer nou, suite proporcional:

    FTT_TEST_DB=test_ftt_f43 venv/bin/python manage.py test \
        fhort.patterns.tests_seam_signals --settings=fhort.settings_test --keepdb

Què defensa cada classe:

1. `AplicabilitatTest` — una parella es resol per SLUG i la cara no hi discrimina, que és
   el que el material real imposa.
2. `GrausTest` — core/common/rara segons els llindars, i el zero mesurat com a mena pròpia.
3. `AsimetriaD02Test` — 🚨 el mirall d'una costura d'un sol sentit no es proposa MAI, ni amb
   la geometria perfecta.
4. `SenyalsAlMotorTest` — els senyals se sumen (amb el seu pes declarat), surten al desglòs
   i no habiliten res que la geometria no sostingui.
5. `PrecedentTest` — la transferència va per rol de vora, i un model no és precedent de si
   mateix.
6. `LeaveOneOutTest` — a escala real: el mecanisme de trobar la parella bona amb els dos
   senyals posats (el leave-one-out contra les 8 costures REALS viu a `ops/recognition/
   lab_seams.py`, que és on hi ha material per fer-lo).
7. `NoTocaLIdentitatTest` — confirmar una costura no escriu cap rol, i el proposador no
   escriu res en absolut.
"""
import math

from django.db import connection
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from fhort.patterns.engine.seam_matching import (LLINDAR_PROPOSTA, PES_CATALEG, Candidat,
                                                 avaluar, proposar, senyal_cataleg,
                                                 senyal_precedent)
from fhort.patterns.recognition.seam_expectations import (CORE, COMMON, NEVER, RARE, Costat,
                                                          Expectativa, SeamExpectations,
                                                          _grau)
from fhort.patterns.recognition.seam_precedent import Precedent, SeamPrecedents, _solapament

MM = 10.0


def _exp(pa, ea, pb, eb, seams, den, fa='', fb='', kind='union'):
    grau, ratio = _grau(seams, den)
    return Expectativa(a=Costat(pa, fa, ea), b=Costat(pb, fb, eb), seam_kind=kind,
                       grau=grau, ratio=ratio, observed_seams=seams, observed_den=den,
                       co_generated=False)


#: Les tres files que el catàleg real porta i que aquests tests fan servir, amb els seus
#: números de debò: així un canvi de llindar es veu contra el material i no contra invents.
LATERAL = _exp('back', 'side_seam', 'front', 'side_seam', 436842, 90273, 'back', 'front')
SISA_BONA = _exp('front', 'armhole', 'sleeve', 'sleeve_cap', 105612, 90273, 'front', 'front')
SISA_MIRALL = _exp('back', 'armhole', 'sleeve', 'sleeve_cap', 0, 90273, 'back', 'front')
COLL = _exp('collar', 'collar_attach', 'front', 'neckline', 14154, 90273, 'front', 'front')


def _cand(sid, pid, nom, role='', edge='', face='', llarg=250.0, piquets=()):
    return Candidat(segment_id=sid, piece_id=pid, piece_nom=nom, vora=1,
                    t_inici=0.0, t_fi=0.25, longitud_mm=llarg, piquets=tuple(piquets),
                    piece_role=role, face=face, edge_role=edge)


class AplicabilitatTest(SimpleTestCase):

    def test_una_parella_es_resol_per_slug(self):
        idx = SeamExpectations([LATERAL])
        e = idx.per_parella(Costat('front', '', 'side_seam'), Costat('back', '', 'side_seam'))
        self.assertIsNotNone(e)
        self.assertEqual(e.grau, CORE)

    def test_la_cara_no_discrimina(self):
        """🚨 Mesurat sobre el banc: casar també per CARA dona 0 de 8 en comptes de 6 de 8.

        Les cinc peces del 837 porten `face = ''` amb tota la raó —D1 va posar l'eix
        davant/darrere al ROL per a les peces de cos— i les plantilles el deletregen. Si la
        cara identifiqués un costat, el catàleg no reconeixeria ni una costura de la casa.
        """
        idx = SeamExpectations([LATERAL])
        for fa, fb in (('', ''), ('front', 'back'), ('back', 'front'), ('', 'back')):
            self.assertIsNotNone(
                idx.per_parella(Costat('front', fa, 'side_seam'),
                                Costat('back', fb, 'side_seam')),
                'la cara {}/{} no hauria de canviar la parella'.format(fa, fb))

    def test_sense_rol_de_vora_el_cataleg_calla(self):
        """Un tram sense nom no és una parella desconeguda: és una pregunta no feta."""
        idx = SeamExpectations([LATERAL])
        self.assertIsNone(idx.per_parella(Costat('front', '', ''), Costat('back', '', 'side_seam')))
        self.assertIsNone(idx.costat_de(_cand(1, 1, 'A', role='front')))

    def test_una_parella_que_el_cataleg_no_te_no_diu_res(self):
        idx = SeamExpectations([LATERAL])
        self.assertIsNone(
            idx.per_parella(Costat('collar', '', 'collar_attach'), Costat('sleeve', '', 'cuff_line')))


class GrausTest(SimpleTestCase):

    def test_els_tres_graus_i_el_zero(self):
        self.assertEqual(_grau(436842, 90273)[0], CORE)
        self.assertEqual(_grau(45000, 90273)[0], COMMON)      # 0,50
        self.assertEqual(_grau(14154, 90273)[0], RARE)        # 0,157
        self.assertEqual(_grau(0, 90273)[0], NEVER)

    def test_sense_denominador_no_es_evidencia(self):
        """Cap denominador no és zero: és una fila que ningú no ha mesurat.

        Es queda com a vocabulari utilitzable i com a evidència inutilitzable — la mateixa
        honestedat que `LandmarkRole.evidence_num = NULL`.
        """
        self.assertEqual(_grau(None, None)[0], RARE)
        self.assertEqual(_grau(10, 0)[0], RARE)

    def test_rara_no_vol_dir_dolenta(self):
        """🚨 `collar_attach↔neckline` mesura 0,157 i el 837 la porta.

        Una rara no encapçala cap checklist, però es proposa i s'anota igual: llegir «rara»
        com a «malament» seria dir-li al patronista que el seu propi vestit és un error.
        """
        idx = SeamExpectations([COLL])
        e = idx.per_parella(Costat('collar', '', 'collar_attach'), Costat('front', '', 'neckline'))
        self.assertEqual(e.grau, RARE)
        self.assertTrue(e.proposable)
        self.assertEqual(idx.esperades([e.a, e.b]), [])

    def test_el_checklist_nomes_mira_els_costats_que_hi_ha(self):
        idx = SeamExpectations([LATERAL, SISA_BONA])
        nomes_laterals = [Costat('front', '', 'side_seam'), Costat('back', '', 'side_seam')]
        self.assertEqual([e.grau for e in idx.esperades(nomes_laterals)], [CORE])


class AsimetriaD02Test(SimpleTestCase):
    """🚨 LLEI D.02 · el mirall d'una costura d'un sol sentit no es proposa MAI."""

    def test_el_zero_mesurat_no_es_proposable(self):
        self.assertFalse(SISA_MIRALL.proposable)
        self.assertTrue(SISA_BONA.proposable)

    def test_la_direccio_bona_puntua_i_la_inversa_TOMBA_la_proposta(self):
        """I tomba, no descompta: amb la geometria perfecta un descompte es recuperaria."""
        idx = SeamExpectations([SISA_BONA, SISA_MIRALL])
        bona_a = _cand(1, 1, 'FRONT', 'front', 'armhole')
        bona_b = _cand(2, 2, 'SLEEVE', 'sleeve', 'sleeve_cap')
        _s, veto = senyal_cataleg(bona_a, bona_b, idx)
        self.assertFalse(veto)

        mirall_a = _cand(3, 3, 'BACK', 'back', 'armhole')
        s, veto = senyal_cataleg(mirall_a, bona_b, idx)
        self.assertTrue(veto)
        self.assertTrue(s.dades['veto'])

        # Geometria PERFECTA: mateixos piquets, mateixa longitud. I tot i així, res.
        pq = (0.1, 0.5, 0.9)
        self.assertIsNone(avaluar(
            _cand(3, 3, 'BACK', 'back', 'armhole', llarg=300.0, piquets=pq),
            _cand(2, 2, 'SLEEVE', 'sleeve', 'sleeve_cap', llarg=300.0, piquets=pq),
            idx, None))

    def test_la_parella_es_queda_amb_la_lectura_mes_forta(self):
        """`armhole↔sleeve_cap` hi és com a 105 612 i com a 0. La parella val el 105 612.

        Llegir el zero com el veredicte de la PARELLA vetaria la costura més comuna del
        corpus; el zero parla d'una DIRECCIÓ, i les direccions es tracten per plantilla.
        """
        idx = SeamExpectations([SISA_MIRALL, SISA_BONA])
        e = idx.per_parella(Costat('front', '', 'armhole'), Costat('sleeve', '', 'sleeve_cap'))
        self.assertEqual(e.grau, CORE)


class SenyalsAlMotorTest(SimpleTestCase):

    PIQUETS = (0.1, 0.5, 0.9)

    def _parella(self):
        return (_cand(1, 1, 'FRONT', 'front', 'side_seam', llarg=600.0, piquets=self.PIQUETS),
                _cand(2, 2, 'BACK', 'back', 'side_seam', llarg=600.0, piquets=self.PIQUETS))

    def test_el_senyal_surt_al_desglos_amb_els_numeros_de_la_plantilla(self):
        a, b = self._parella()
        p = avaluar(a, b, SeamExpectations([LATERAL]), None)
        self.assertIsNotNone(p)
        cat = next(s for s in p.senyals if s.mena == 'cataleg')
        self.assertEqual(cat.dades['observed_seams'], 436842)
        self.assertEqual(cat.dades['observed_den'], 90273)
        self.assertEqual(cat.dades['grau'], CORE)

    def test_el_pes_declarat_es_el_que_se_suma(self):
        """El senyal suma EXACTAMENT `PES_CATALEG`, sigui quin sigui el seu valor.

        Escrit contra la constant i no contra un número: el dia que el banc permeti pesar-lo
        i algú la mogui, aquest test ha de seguir sent cert, i el que ha de canviar és la
        confiança — no la prova.
        """
        a, b = self._parella()
        sense = avaluar(a, b, None, None)
        amb = avaluar(a, b, SeamExpectations([LATERAL]), None)
        self.assertAlmostEqual(amb.confianca, min(1.0, sense.confianca + PES_CATALEG), places=3)

    def test_el_cataleg_no_habilita_res_que_la_geometria_no_sostingui(self):
        """La porta segueix sent NOMÉS geomètrica, com amb el costum del taller.

        Dos trams de longituds incompatibles i sense piquets no es proposen encara que el
        catàleg els aparelli de nucli: si una expectativa pogués obrir la porta, el motor
        proposaria pel que la gent sol fer i no pel que aquesta peça diu.
        """
        a = _cand(1, 1, 'FRONT', 'front', 'side_seam', llarg=600.0)
        b = _cand(2, 2, 'BACK', 'back', 'side_seam', llarg=120.0)
        self.assertIsNone(avaluar(a, b, SeamExpectations([LATERAL]), None))

    def test_sense_index_el_motor_es_comporta_com_abans(self):
        a, b = self._parella()
        p = avaluar(a, b, None, None)
        self.assertIsNotNone(p)
        self.assertNotIn('cataleg', {s.mena for s in p.senyals})
        self.assertNotIn('precedent', {s.mena for s in p.senyals})


class PrecedentTest(SimpleTestCase):

    def _banc(self):
        clau = frozenset((('front', 'side_seam'), ('back', 'side_seam')))
        return SeamPrecedents([Precedent(clau=clau, model_id=1383, model_nom='837 VESTIT',
                                         seam_kind='union')])

    def test_la_transferencia_va_per_rol_de_vora(self):
        banc = self._banc()
        # Una peça d'un ALTRE patró, amb una geometria que no s'assembla a res del 837.
        a = _cand(9, 9, 'QUALSEVOL', 'front', 'side_seam', llarg=17.0)
        b = _cand(10, 10, 'ALTRA', 'back', 'side_seam', llarg=17.0)
        s = senyal_precedent(a, b, banc)
        self.assertIn('837 VESTIT', s.detall)
        self.assertEqual(s.dades['model'], 1383)

    def test_sense_rol_de_vora_no_hi_ha_precedent(self):
        s = senyal_precedent(_cand(1, 1, 'A', 'front'), _cand(2, 2, 'B', 'back'), self._banc())
        self.assertEqual(s.detall, '')

    def test_labsencia_de_precedent_no_es_evidencia_en_contra(self):
        """Un banc de vuit costures que digués «no» seria un banc opinant sobre el que no ha vist."""
        s = senyal_precedent(
            _cand(1, 1, 'A', 'collar', 'collar_attach'),
            _cand(2, 2, 'B', 'front', 'neckline'), self._banc())
        self.assertEqual(s.punts, 0.0)

    def test_el_solapament_tracta_els_rangs_que_embolcallen(self):
        """🚨 Un `t_fi < t_inici` passa per l'origen de la vora, i min/max hi menteix.

        Mesurat a la FASE 0: sense això, una sisa d'esquena casava contra l'escot.
        """
        # El tram [0,9 → 0,1] embolcalla i toca [0,95 → 0,98]; un min/max en diria zero.
        self.assertAlmostEqual(_solapament(0.9, 0.1, 0.95, 0.98), 0.03, places=6)
        self.assertAlmostEqual(_solapament(0.9, 0.1, 0.02, 0.05), 0.03, places=6)
        self.assertAlmostEqual(_solapament(0.1, 0.4, 0.5, 0.6), 0.0, places=6)


class LeaveOneOutTest(SimpleTestCase):
    """Amagar una costura i tornar-la a trobar, sobre geometria a ESCALA REAL.

    🚨 Mil·límetres de debò. Un cos de 600 mm de costat amb piquets a 0,1/0,5/0,9 és una
    peça; dos trams de 3 unitats passarien els llindars sense dir res d'un vestit.

    El leave-one-out contra les 8 costures REALS del banc viu a
    `ops/recognition/lab_seams.py`, que és on hi ha material per fer-lo. Aquí es prova el
    MECANISME: que amb els dos senyals posats el motor segueix trobant la parella bona i
    seguint repartint sense conflictes.
    """

    PIQUETS = (0.12, 0.48, 0.91)

    def _patro(self):
        """Un davant i una esquena amb dos laterals cadascun, com un cos de debò."""
        return [
            _cand(1, 1, 'FRONT', 'front', 'side_seam', llarg=604.0, piquets=self.PIQUETS),
            _cand(2, 1, 'FRONT', 'front', 'hem', llarg=627.0),
            _cand(3, 2, 'BACK', 'back', 'side_seam', llarg=604.0, piquets=self.PIQUETS),
            _cand(4, 2, 'BACK', 'back', 'hem', llarg=627.0),
        ]

    def test_la_parella_bona_es_troba_amb_els_dos_senyals_posats(self):
        idx = SeamExpectations([LATERAL])
        clau = frozenset((('front', 'side_seam'), ('back', 'side_seam')))
        banc = SeamPrecedents([Precedent(clau=clau, model_id=1383, model_nom='837 VESTIT',
                                         seam_kind='union')])
        propostes, _desc = proposar(self._patro(), expectatives=idx, precedents=banc)
        parelles = {frozenset((p.a.segment_id, p.b.segment_id)) for p in propostes}
        self.assertIn(frozenset((1, 3)), parelles)
        guanyadora = next(p for p in propostes if {p.a.segment_id, p.b.segment_id} == {1, 3})
        menes = {s.mena for s in guanyadora.senyals}
        self.assertIn('cataleg', menes)
        self.assertIn('precedent', menes)

    def test_un_tram_no_es_reparteix_dues_vegades(self):
        """La restricció global es manté amb els senyals nous: cosir la mateixa tela dos cops
        seria el defecte que `validar_cobertura` denuncia, i cap senyal nou l'ha d'obrir."""
        propostes, _d = proposar(self._patro(), expectatives=SeamExpectations([LATERAL]))
        vistos = []
        for p in propostes:
            vistos += [p.a.segment_id, p.b.segment_id]
        self.assertEqual(len(vistos), len(set(vistos)))


class NoTocaLIdentitatTest(TenantTestCase):
    """🚨 Confirmar una costura NO toca la identitat ni els rols de vora.

    F4.3 llegeix `piece_role` i `edge_role` per construir els seus senyals. Llegir-los és
    tota la relació que hi ha de tenir: el dia que confirmar una costura escrivís un rol,
    el sistema estaria aprenent del seu propi encert, que és exactament el que
    `PatternPiece.rol_origen` existeix per fer visible.
    """

    def test_els_serveis_de_costura_no_declaren_cap_camp_didentitat(self):
        from fhort.patterns.recognition import edge_service, service

        # Les úniques llistes d'escriptura de la família. Cap de les dues no ha de créixer
        # sense que aquest test ho digui.
        self.assertEqual(edge_service.UPDATE_FIELDS, ['edge_role'])
        self.assertEqual(
            service.UPDATE_FIELDS,
            ['proposed_role', 'proposed_face', 'proposed_score', 'proposed_evidence',
             'proposed_at'])
        for camp in ('piece_role', 'face', 'rol_origen', 'nom'):
            self.assertNotIn(camp, edge_service.UPDATE_FIELDS)
            self.assertNotIn(camp, service.UPDATE_FIELDS)

    def test_el_proposador_de_costures_no_escriu_res(self):
        """`seam_proposals` és lectura de cap a peus, i es comprova al codi, no de paraula."""
        import inspect

        from fhort.patterns import seam_proposals

        font = inspect.getsource(seam_proposals)
        for prohibit in ('.save(', '.create(', '.delete(', '.update('):
            self.assertNotIn(prohibit, font,
                             'seam_proposals no pot escriure: hi ha «{}»'.format(prohibit))
