"""S45/B · MESURAR PRENDA NO EXIGEIX PROPAGAT — i PROPAGAR segueix exigint graduació.

Substrat: `docs/ordres/DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §B.

── QUÈ CANVIA I PER QUÈ ─────────────────────────────────────────────────────────────────
El guard de `create_piece_fitting` («el model no té cap GradingVersion activa. Cal generar
les talles primer») era el guard de PROPAGAR dit a la porta de MESURAR. Tancava el cas que
el domini sí que admet —regla d'Agus, Patró C—: un PROTOTIP arriba a la sala sense graduació
definida i la modista l'ha de poder anotar.

EL GUARD ES PARTEIX PER CAMÍ (llei S43), i aquest banc n'exercita **els dos costats**:
  · MESURAR PRENDA sobre un model sense cap `GradingVersion` → la peça neix;
  · PROPAGAR sense regles → segueix sent 400, amb el mateix missatge de sempre.

🚨 **EL VERMELL D'AQUEST BANC ABANS DEL CANVI**: `test_create_piece_sense_grading_version_
obre_la_presa` donava 400 amb «no té cap GradingVersion activa». Les proves del costat de
propagar ja passaven, i han de seguir passant: és la meitat que NO es toca.

── LA TROBALLA QUE FA QUE AIXÒ NO SIGUI UNA DECISIÓ DE DOMINI ──────────────────────────
§B.5 de la diagnosi donava el fix per BLOQUEJAT: «d'on surt `valor_teoric` d'una línia si no
hi ha `GradedSpec`? Decisió d'Agus». La resposta ja estava CONSTRUÏDA i ningú l'havia vista:
`reconcilia_linies` (`services.py:640-660`) ja sap néixer sense spec i cau a la talla base
del model. Aquest banc ho segella (`test_les_linies_surten_de_la_TALLA_BASE`): si algú retira
aquell fallback, aquí es posa vermell i no en un fitting real.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import (
    FittingSession, GradedSpec, GradingVersion, PieceFitting, PieceFittingLine, SizeFitting,
)
from fhort.fitting.services import seal_model_grading
from fhort.fitting.views import FittingSessionViewSet
from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.views import generate_grading_view
from fhort.pom.models import GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem

BASE = 'M'
TALLES = ['S', 'M', 'L', 'XL']


class ProtoSenseGraduacioBase(TenantTestCase):
    """Un PROTO: run, talla base i mesures base — i CAP regla, CAP GradingVersion."""

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
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='tester_s45b')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_S45B', nom='SS S45B', base_unit='ALPHA')
        self.talles = {et: SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
                       for i, et in enumerate(TALLES, start=1)}
        self.pom = POMMaster.objects.create(codi_client='PS45B', nom_client='POM S45B')
        self.model = Model.objects.create(
            codi_intern='S45B-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='·'.join(TALLES), base_size_label=BASE,
            size_system=self.ss,          # ← CAP grading_rule_set: és un proto
        )
        # La mesura base HI ÉS: el proto es mesura perquè hi ha una peça i una xifra a anotar.
        self.bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=48.0, is_active=True)
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 21),
        )
        # 🔑 EL PUNT DE PARTIDA DEL BANC: cap GradingVersion. El signal de Model pot haver
        # materialitzat el SizeFitting (i està bé: la peça l'ha d'adoptar), però la versió no.
        GradingVersion.objects.filter(size_fitting__model=self.model).delete()

        self.factory = APIRequestFactory()
        self.create_piece_view = FittingSessionViewSet.as_view({'post': 'create_piece'})

    def _create_piece(self):
        req = self.factory.post('/create-piece/', {'model_id': self.model.pk}, format='json')
        force_authenticate(req, user=self.user)
        return self.create_piece_view(req, pk=self.session.pk)

    def _propagar(self):
        req = self.factory.post('/generar-grading/', {}, format='json')
        force_authenticate(req, user=self.user)
        return generate_grading_view(req, model_id=self.model.pk)


class MesurarPrendaSObreTest(ProtoSenseGraduacioBase):
    """LA MEITAT QUE S'OBRE: la presa d'un proto sense graduació."""

    def test_de_partida_el_model_NO_te_cap_grading_version(self):
        """Control del fixture: si això falla, la resta del banc no prova res."""
        self.assertFalse(
            GradingVersion.objects.filter(size_fitting__model=self.model).exists())

    def test_create_piece_sense_grading_version_obre_la_presa(self):
        """🔴→🟢 El cas d'Agus: el proto arriba a la sala i s'ha de poder anotar."""
        resp = self._create_piece()
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        self.assertEqual(resp.data['n_linies'], 1)
        self.assertEqual(PieceFitting.objects.filter(
            session=self.session, model=self.model).count(), 1)

    def test_les_linies_surten_de_la_TALLA_BASE(self):
        """🔑 I NO CAL DECIDIR RES: `reconcilia_linies` ja cau a la base quan no hi ha spec.

        Una línia i una sola —la de la M—, amb el teòric de `BaseMeasurement`. Les altres
        talles no hi són perquè encara no existeixen: no s'inventa cap corba.
        """
        self._create_piece()
        pf = PieceFitting.objects.get(session=self.session, model=self.model)
        linies = list(PieceFittingLine.objects.filter(piece_fitting=pf))
        self.assertEqual([l.size_label for l in linies], [BASE])
        self.assertEqual(float(linies[0].valor_teoric), 48.0)
        self.assertEqual(float(linies[0].valor_real), 48.0)
        self.assertEqual(linies[0].pom_id, self.pom.pk)

    def test_la_versio_materialitzada_neix_BUIDA_i_no_diu_que_hi_hagi_taula(self):
        """Obrir una presa NO és propagar, i cap superfície ho ha de poder confondre."""
        self._create_piece()
        gv = GradingVersion.objects.get(size_fitting__model=self.model)
        self.assertTrue(gv.is_active)
        self.assertFalse(gv.aprovada)
        self.assertEqual(gv.version_number, 1)
        # el predicat de `te_taula` (`models_app/views.py:3858`) segueix sent FALS
        self.assertFalse(
            GradedSpec.objects.filter(grading_version=gv, is_active=True).exists())

    def test_una_versio_BUIDA_no_es_segella(self):
        """Un segell sobre el no-res bloquejaria la primera propagació de debò (guard D-1)."""
        self._create_piece()
        self.assertIsNone(seal_model_grading(self.model, user_profile_id=self.profile.pk))
        gv = GradingVersion.objects.get(size_fitting__model=self.model)
        self.assertFalse(gv.aprovada)

    def test_obrir_dues_vegades_no_crea_dues_versions(self):
        """La segona crida troba l'activa i l'adopta: el camí lliure no és una fàbrica."""
        self._create_piece()
        PieceFitting.objects.filter(session=self.session).delete()
        self._create_piece()
        self.assertEqual(
            GradingVersion.objects.filter(size_fitting__model=self.model).count(), 1)


class PropagarSegueixTancatTest(ProtoSenseGraduacioBase):
    """LA MEITAT QUE ES QUEDA TANCADA: propagar exigeix graduació. CAP CANVI."""

    def test_propagar_sense_regles_segueix_sent_400(self):
        resp = self._propagar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('regles de grading', resp.data['error'])

    def test_propagar_sense_regles_segueix_sent_400_TAMBE_amb_la_presa_oberta(self):
        """🚨 EL CAS QUE PROVA QUE EL GUARD ESTÀ PARTIT DE DEBÒ.

        La versió buida que materialitza la presa NO pot obrir la porta de propagar: si
        `generate_grading_view` mirés la VERSIÓ en lloc de les REGLES, aquí passaria — i
        propagar sobre un model sense regles és exactament el que la regla d'Agus prohibeix.
        """
        self._create_piece()
        resp = self._propagar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('regles de grading', resp.data['error'])
        self.assertFalse(GradedSpec.objects.filter(
            grading_version__size_fitting__model=self.model).exists())


class ModelGraduatNoCanviaTest(ProtoSenseGraduacioBase):
    """CONTROL DE NO-REGRESSIÓ: un model amb regles i versió activa es comporta igual."""

    def setUp(self):
        super().setUp()
        self.rs = GradingRuleSet.objects.create(nom='RS S45B')
        GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.talles[BASE],
            logica='LINEAR', increment_base=2,
        )
        self.model.grading_rule_set = self.rs
        self.model.save(update_fields=['grading_rule_set'])

    def test_propagar_amb_regles_genera_specs(self):
        resp = self._propagar()
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertTrue(GradedSpec.objects.filter(
            grading_version__size_fitting__model=self.model, is_active=True).exists())

    def test_la_presa_sobre_un_model_PROPAGAT_porta_TOTES_les_talles(self):
        """El camí de sempre: amb specs, la peça clona la corba sencera."""
        self._propagar()
        resp = self._create_piece()
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        pf = PieceFitting.objects.get(session=self.session, model=self.model)
        self.assertEqual(
            sorted({l.size_label for l in PieceFittingLine.objects.filter(piece_fitting=pf)}),
            sorted(TALLES))

    def test_una_versio_AMB_specs_SI_que_es_segella(self):
        """L'altra meitat del guard del segell: el que promet alguna cosa, se signa."""
        self._propagar()
        self.assertIsNotNone(seal_model_grading(self.model, user_profile_id=self.profile.pk))
