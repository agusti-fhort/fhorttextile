"""Tests del catàleg semàntic (F3 · Patró B, 2026-08-26).

Fitxer NOU i a part de `pom/tests.py` per la llei de suites proporcionals: aquest tram
s'executa sol —`manage.py test fhort.pom.tests_semantic_catalog`— i no arrossega la suite
sencera de `pom`, que és d'una altra feina i d'un altre dia.

    venv/bin/python manage.py test fhort.pom.tests_semantic_catalog \
        --settings=fhort.settings_test --keepdb

Els cinc que la Fase C demana, i cadascun defensa una frase:

1. **L'ordenació canònica ÉS un pany, no una convenció escrita.** (a,b) i (b,a) han de
   ser la mateixa fila, i el UNIQUE ho ha de fer complir a la BD.
2. **La sembra és idempotent de debò**: segona passada, zero creats i zero duplicats.
3. **`edge_role` és RESTRICT**: un rol de vora que un segment reclama no desapareix.
4. **L'HPS es DERIVA**: la regla de `LandmarkRole` resol sobre un mini-graf sintètic.
5. **El mapa GC→FTT resol sencer**: cap dels 24 rols apunta a un slug que no existeix.
"""
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.db.models import RestrictedError
from django_tenants.test.cases import TenantTestCase

from fhort.patterns.models import PatternFile, PatternPiece, PatternSegment
from fhort.pom.landmarks import LandmarkNoResolt, Tram, resol_landmark
from fhort.pom.management.commands.seed_pattern_piece_roles import (
    ROLS, sembra as sembra_rols)
from fhort.pom.management.commands.seed_semantic_catalog import (
    EDGE_ROLES, GC_MAP, LANDMARK_ROLES, SEAM_PAIRS, sembra as sembra_cataleg)
from fhort.pom.models import (
    EdgeRole, GarmentType, GCPieceRoleMap, LandmarkRole, PatternPieceRole,
    SeamPairTemplate)
from fhort.tasks.models import GarmentTypeItem


class _Base(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant F3'


class OrdenacioCanonicaTest(_Base):
    """🚨 La mateixa costura, escrita al revés, ha de ser LA MATEIXA FILA.

    Sense això el catàleg es duplica en silenci: ningú no mira una taula de 53 files per
    veure si `front↔back` i `back↔front` hi són totes dues, i un aparellador que en
    trobés les dues comptaria cada costura dos cops.
    """

    def test_ordena_es_simetrica(self):
        a = ('front', 'front', 'shoulder_seam')
        b = ('back', 'back', 'shoulder_seam')
        self.assertEqual(SeamPairTemplate.ordena(a, b), SeamPairTemplate.ordena(b, a))
        # I l'ordre és el que la llei diu: (piece_role, face, edge_role).
        self.assertEqual(SeamPairTemplate.ordena(a, b)[0], b)

    def test_save_canonitza_encara_que_l_entrada_vingui_girada(self):
        t = SeamPairTemplate.objects.create(
            seam_kind=SeamPairTemplate.KIND_UNION,
            piece_role_a_slug='front', face_a='front', edge_role_a_slug='shoulder_seam',
            piece_role_b_slug='back', face_b='back', edge_role_b_slug='shoulder_seam')
        t.refresh_from_db()
        self.assertEqual(t.piece_role_a_slug, 'back')
        self.assertEqual(t.piece_role_b_slug, 'front')

    def test_a_b_i_b_a_son_una_sola_fila(self):
        """El pany de debò: el UNIQUE ha de petar, no l'ORM per educació.

        🚨 Aquest test va donar VERMELL amb un sol `UniqueConstraint` sobre les 8 columnes
        i **la fila duplicada va entrar**: `garment_type_item` és nul·lable, a Postgres dos
        NULL no són iguals, i totes les plantilles que F3 sembra són genèriques —o sigui
        que el UNIQUE no en protegia ni una. La constraint parcial va néixer d'aquí.
        """
        SeamPairTemplate.objects.create(
            seam_kind=SeamPairTemplate.KIND_UNION,
            piece_role_a_slug='front', face_a='front', edge_role_a_slug='shoulder_seam',
            piece_role_b_slug='back', face_b='back', edge_role_b_slug='shoulder_seam')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SeamPairTemplate.objects.create(
                    seam_kind=SeamPairTemplate.KIND_UNION,
                    piece_role_a_slug='back', face_a='back',
                    edge_role_a_slug='shoulder_seam',
                    piece_role_b_slug='front', face_b='front',
                    edge_role_b_slug='shoulder_seam')
        self.assertEqual(SeamPairTemplate.objects.count(), 1)


class IdempotenciaDeLaSembraTest(_Base):
    """La segona passada no crea res. **I la tercera tampoc.**

    Es corre SENSE corpus a posta: el que aquest test defensa és la clau natural, no les
    xifres. Amb corpus caldria una BD de tercers viva per veure verd, i un test que depèn
    d'una BD que pot no ser-hi és un test que un dia dirà vermell sense que res s'hagi
    trencat.
    """

    def _sembra(self):
        return sembra_cataleg(self.tenant.schema_name, cens=None, meta={})

    def test_primera_passada_crea_i_segona_no(self):
        r1 = self._sembra()
        self.assertEqual(r1['edge_roles'], [len(EDGE_ROLES), 0])
        self.assertEqual(r1['landmark_roles'], [len(LANDMARK_ROLES), 0])
        self.assertEqual(r1['seam_pairs'], [len(SEAM_PAIRS), 0])
        self.assertEqual(r1['gc_map'], [len(GC_MAP), 0])

        r2 = self._sembra()
        self.assertEqual(r2['edge_roles'], [0, len(EDGE_ROLES)])
        self.assertEqual(r2['landmark_roles'], [0, len(LANDMARK_ROLES)])
        self.assertEqual(r2['seam_pairs'], [0, len(SEAM_PAIRS)])
        self.assertEqual(r2['gc_map'], [0, len(GC_MAP)])

        self._sembra()
        self.assertEqual(EdgeRole.objects.count(), len(EDGE_ROLES))
        self.assertEqual(LandmarkRole.objects.count(), len(LANDMARK_ROLES))
        self.assertEqual(SeamPairTemplate.objects.count(), len(SEAM_PAIRS))
        self.assertEqual(GCPieceRoleMap.objects.count(), len(GC_MAP))

    def test_sense_corpus_els_observed_queden_a_NULL_i_no_a_zero(self):
        """«No s'ha mesurat» i «mesurat i surt zero» no s'han de poder confondre."""
        self._sembra()
        self.assertEqual(
            SeamPairTemplate.objects.filter(observed_seams__isnull=True).count(),
            len(SEAM_PAIRS))
        self.assertEqual(SeamPairTemplate.objects.filter(observed_seams=0).count(), 0)

    def test_cap_plantilla_no_apunta_a_un_rol_de_vora_inexistent(self):
        """El catàleg ha de tancar sobre si mateix: si no, F4 llegirà slugs morts."""
        self._sembra()
        vores = set(EdgeRole.objects.values_list('slug', flat=True))
        for t in SeamPairTemplate.objects.all():
            self.assertIn(t.edge_role_a_slug, vores, msg=str(t))
            self.assertIn(t.edge_role_b_slug, vores, msg=str(t))
        # …i els `mates_slug` també, que són l'altra meitat de la gramàtica.
        for r in EdgeRole.objects.exclude(mates_slug=''):
            self.assertIn(r.mates_slug, vores, msg=r.slug)


class EdgeRoleRestrictTest(_Base):
    """Un rol de vora que algun segment reclama **no pot desaparèixer**.

    ⚠️ Django no emet cap `ON DELETE` a la BD: `RESTRICT` el fa complir l'ORM, igual que
    `PROTECT`. Per això el test esborra per l'ORM, que és per on passa tot el sistema —i
    per això el report ho diu, perquè un `\\d` no mostrarà mai aquesta llei.
    """

    def _segment_amb_rol(self):
        rol = EdgeRole.objects.create(
            slug='qa_side_seam', nom_en='QA', nom_ca='QA', nom_es='QA',
            zone='torso', kind=EdgeRole.KIND_SEAM)
        # ⚠️ `patternfile_xor_model_item` exigeix EXACTAMENT un dels dos pares. Un
        # `PatternFile` orfe no existeix ni per a un test: es penja d'un GTI de biblioteca,
        # que és el camí que la llei ja admet.
        gt = GarmentType.objects.create(codi_client='QA', nom_client='QA', grup='QA')
        gti = GarmentTypeItem.objects.create(garment_type=gt, code='qa', name='QA')
        pf = PatternFile.objects.create(nom_fitxer='qa.dxf', garment_type_item=gti)
        peca = PatternPiece.objects.create(pattern_file=pf, nom_block='QA-1')
        seg = PatternSegment.objects.create(piece=peca, vora=0, t_inici=0.0, t_fi=1.0,
                                            edge_role=rol)
        return rol, seg

    def test_esborrar_un_rol_reclamat_bloqueja(self):
        rol, _ = self._segment_amb_rol()
        with self.assertRaises(RestrictedError):
            rol.delete()
        self.assertTrue(EdgeRole.objects.filter(pk=rol.pk).exists())

    def test_un_rol_sense_segments_si_que_s_esborra(self):
        """El pany ha de tancar la porta justa: si no, no és un pany, és un mur."""
        rol = EdgeRole.objects.create(
            slug='qa_orfe', nom_en='QA', nom_ca='QA', nom_es='QA',
            zone='any', kind=EdgeRole.KIND_SEAM)
        rol.delete()
        self.assertFalse(EdgeRole.objects.filter(slug='qa_orfe').exists())

    def test_el_nom_lliure_conviu_amb_el_rol(self):
        """`nom` no el substitueix el rol: el rol diu QUÈ és, `nom` com en diu el taller."""
        rol, seg = self._segment_amb_rol()
        seg.nom = 'costat de sota la sisa'
        seg.save(update_fields=['nom'])
        seg.refresh_from_db()
        self.assertEqual(seg.edge_role_id, rol.pk)
        self.assertEqual(seg.nom, 'costat de sota la sisa')


class DerivacioDeLandmarksTest(_Base):
    """🔑 L'HPS es CALCULA. És la resposta al bloquejant A11.

    El mini-graf és el contorn d'un mig-davant de cos, amb els rols que un reconeixedor o
    un patronista hi haurà posat. Els punts són tuples `(x, y)` perquè un dels desempats
    (`lowest_y`) els llegeix; la resta de regles els tracta com a identitats opaques.

        (0,10) HPS ──escot── (4,10) centre d'escot
           │                        │
        espatlla                 centre davant
           │                        │
        (1,8) punt d'espatlla       │
           │                        │
         sisa                       │
           │                        │
        (1,5) sota-braç ──cintura── (4,5)
    """

    HPS = (0, 10)
    ESPATLLA = (1, 8)
    SOTABRAC = (1, 5)
    ESCOT_CENTRE = (4, 10)
    CINTURA_COSTAT = (1, 5)

    GRAF = [
        Tram('neckline', (0, 10), (4, 10)),
        Tram('shoulder_seam', (0, 10), (1, 8)),
        Tram('armhole', (1, 8), (1, 5)),
        Tram('centre_front', (4, 10), (4, 5)),
        Tram('side_seam', (1, 5), (1, 2)),
        Tram('waistline', (1, 5), (4, 5)),
    ]

    def _regla(self, slug):
        return LandmarkRole.objects.get(slug=slug)

    def setUp(self):
        super().setUp()
        sembra_cataleg(self.tenant.schema_name, cens=None, meta={})

    def test_hps_es_l_extrem_compartit_per_escot_i_espatlla(self):
        self.assertEqual(resol_landmark(self._regla('hps'), self.GRAF), self.HPS)

    def test_punt_d_espatlla_es_l_altre_cap_del_mateix_pont(self):
        self.assertEqual(
            resol_landmark(self._regla('shoulder_point'), self.GRAF), self.ESPATLLA)

    def test_sotabrac_es_el_cap_llunya_de_la_sisa(self):
        resolts = {'shoulder_point': self.ESPATLLA}
        self.assertEqual(
            resol_landmark(self._regla('underarm_point'), self.GRAF, resolts),
            self.SOTABRAC)

    def test_centre_d_escot_es_el_cap_llunya_de_l_escot(self):
        self.assertEqual(
            resol_landmark(self._regla('neck_centre_point'), self.GRAF,
                           {'hps': self.HPS}),
            self.ESCOT_CENTRE)

    def test_cintura_al_costat(self):
        self.assertEqual(
            resol_landmark(self._regla('waist_side_point'), self.GRAF),
            self.CINTURA_COSTAT)

    def test_una_vora_que_falta_no_torna_None_sino_que_es_queixa(self):
        """El `None` silenciós acabaria sent un (0,0) tres capes més amunt."""
        graf_sense_espatlla = [t for t in self.GRAF if t.edge_role != 'shoulder_seam']
        with self.assertRaises(LandmarkNoResolt):
            resol_landmark(self._regla('hps'), graf_sense_espatlla)

    def test_derivable_i_operacio_no_es_poden_contradir(self):
        """🚨 La invariant, i no el recompte.

        La versió d'F3 assertava «vuit derivables i cap manual», i la sessió Montse (27/08)
        la va tombar amb raó: els nou punts nous inclouen sis de CORPORALS, que es marquen
        sobre el cos i del patró no surten mai. `derivation_op='manual'` no és un defecte:
        és el registre honest d'això.

        El que sí que ha de ser cert per sempre és que **els dos camps no es contradiguin**.
        Un punt `derivable=True` amb operació `manual` seria una promesa que ningú no pot
        complir —F4 el buscaria i no el trobaria—, i un `derivable=False` amb una operació
        de debò seria una regla escrita que ningú no crida. Un recompte caduca cada vegada
        que el catàleg creix; això no.
        """
        for r in LandmarkRole.objects.all():
            if r.derivable:
                self.assertNotEqual(r.derivation_op, LandmarkRole.OP_MANUAL, msg=r.slug)
                self.assertTrue(r.derivation_input, msg=r.slug)
            else:
                self.assertEqual(r.derivation_op, LandmarkRole.OP_MANUAL, msg=r.slug)
                self.assertEqual(r.derivation_input, {}, msg=r.slug)
        # I que n'hi hagi dels dos: un catàleg amb tot derivable o tot manual voldria dir
        # que algú ha col·lapsat la distinció.
        self.assertGreater(LandmarkRole.objects.filter(derivable=True).count(), 0)
        self.assertGreater(LandmarkRole.objects.filter(derivable=False).count(), 0)

    def test_nomes_dues_regles_porten_evidencia_i_es_la_mateixa(self):
        """No manllevar el 2.371 del veí és la meitat de l'honestedat d'aquesta taula."""
        amb = LandmarkRole.objects.exclude(evidence_num=None)
        self.assertEqual(set(amb.values_list('slug', flat=True)),
                         {'hps', 'shoulder_point'})
        for r in amb:
            self.assertEqual((r.evidence_num, r.evidence_den), (2371, 2371))

    def test_una_regla_no_derivable_no_es_calcula_a_mitges(self):
        regla = SimpleNamespace(derivable=False, derivation_op='manual',
                                derivation_input={}, derivation_tiebreak='')
        with self.assertRaises(LandmarkNoResolt):
            resol_landmark(regla, self.GRAF)


class MapaGCTest(_Base):
    """Els 24 rols de GarmentCode resolen tots: 19 nets + 5 pels tres slugs de D6.

    Aquest és el test que hauria cantat si algú retirés `pant`, `hood` o `godet_insert`
    del seed de rols de peça: el mapa quedaria apuntant al buit i el banc de veïns de F4
    traduiria panells a un slug que no existeix, en silenci i amb 200 OK.
    """

    D6 = {'pant', 'hood', 'godet_insert'}

    def setUp(self):
        super().setUp()
        sembra_rols(self.tenant.schema_name)
        sembra_cataleg(self.tenant.schema_name, cens=None, meta={})

    def test_els_24_apunten_a_un_slug_que_existeix(self):
        slugs = set(PatternPieceRole.objects.values_list('slug', flat=True))
        self.assertEqual(GCPieceRoleMap.objects.count(), 24)
        for fila in GCPieceRoleMap.objects.all():
            self.assertIn(fila.ftt_slug, slugs, msg=fila.gc_role)

    def test_cinc_resolen_NOMES_gracies_a_D6(self):
        via_d6 = GCPieceRoleMap.objects.filter(ftt_slug__in=self.D6)
        self.assertEqual(via_d6.count(), 5)
        self.assertEqual(
            set(via_d6.values_list('gc_role', flat=True)),
            {'pant_f', 'pant_b', 'hood', 'ins_skirt_front', 'ins_skirt_back'})

    def test_els_tres_slugs_de_D6_son_de_sistema_i_de_sembra(self):
        for slug in self.D6:
            r = PatternPieceRole.objects.get(slug=slug)
            self.assertTrue(r.is_system, msg=slug)
            self.assertEqual(r.origen, PatternPieceRole.ORIGEN_SEED, msg=slug)
        self.assertEqual(len(ROLS), 33)

    def test_els_24_cauen_sobre_11_slugs_i_no_mes(self):
        """La col·lisió dels quatre punys és VOLGUDA i ha de quedar mesurada, no suposada."""
        destins = set(GCPieceRoleMap.objects.values_list('ftt_slug', flat=True))
        self.assertEqual(len(destins), 11)
        # VUIT rols de GarmentCode cauen sobre `cuff` (4 conceptes x 2 cares), i l'eix
        # `face` els redueix a DOS destins. Aquest test va donar 8 != 4 la primera vegada:
        # el «quatre» era d'un docstring meu, no d'un recompte.
        punys = GCPieceRoleMap.objects.filter(ftt_slug='cuff')
        self.assertEqual(punys.count(), 8)
        self.assertEqual(set(punys.values_list('face', flat=True)), {'front', 'back'})

    def test_cap_plantilla_no_fa_servir_una_peca_fora_del_cataleg(self):
        slugs = set(PatternPieceRole.objects.values_list('slug', flat=True))
        for t in SeamPairTemplate.objects.all():
            self.assertIn(t.piece_role_a_slug, slugs, msg=str(t))
            self.assertIn(t.piece_role_b_slug, slugs, msg=str(t))
