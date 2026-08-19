"""D-31.21 — EL VEREDICTE DE LA CEL·LA: es desa, es veu, i un REJECTED no sembra.

La llei diu «la darrera mesura VÀLIDA escrita». La paraula que fa la feina és VÀLIDA: una
presa que la modista ha declarat dolenta segueix sent visible —el rebuig és informació, no un
esborrat— però cap camí que sembri o propagui mesures la pot llegir.

ELS DOS CAMINS QUE HI HA, i per què són exactament dos (cens del 04/08):
  1. `consolidate_base_from_fitting` — PieceFittingLine → BaseMeasurement. És l'embut de
     TOTS els camins de sembra: hi passen el tancament del fitting
     (`close_piece_fitting`), la propagació conscient (`models_app/views.py:2554`), la
     derivació a les germanes (`services_derivacio.aplica`, cridada a dins) i el Welford
     (que menja la llista que retorna). Filtrant aquí, els quatre queden coberts alhora.
  2. `PieceFittingLineViewSet.propagar` — l'ancoratge en temps d'edició, que escampa el delta
     de la cel·la a les germanes de TALLA.
Les altres superfícies que toquen `PieceFittingLine` (`pom/s8_views` CSV, `pom/s10_views`
fitting-vs-spec, `fitting/repas_views`) només LLEGEIXEN: no sembren res i no filtren.

Convenció del repo: `python manage.py test fhort.fitting` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.fitting.views import PieceFittingLineViewSet
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import (GradingRule, GradingRuleSet, POMMaster, SizeDefinition,
                              SizeSystem)

TEORICS = {'S': 10.0, 'M': 20.0, 'L': 30.0, 'XL': 40.0}


class _BaseVeredicteTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='modista')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Modista', 'rol_nom': 'admin'})

        ss = SizeSystem.objects.create(codi='SS_V', nom='SS veredicte', base_unit='ALPHA')
        talles = {et: SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
                  for i, et in enumerate(['S', 'M', 'L', 'XL'], start=1)}
        self.rs = GradingRuleSet.objects.create(nom='RS veredicte')
        self.pom = POMMaster.objects.create(codi_client='P1', nom_client='Pit')
        GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=talles['M'],
            logica='LINEAR', increment_base=2,
        )
        self.model = Model.objects.create(
            codi_intern='TST-D3121', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L·XL', base_size_label='M',
            size_system=ss, grading_rule_set=self.rs,
        )
        sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-V-1', 'tipus': 'PRINCIPAL', 'creat_per': self.profile},
        )
        self.gv = GradingVersion.objects.create(
            size_fitting=sf, version_number=1, is_active=True, creat_per=self.profile)
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 4))
        self.pf = PieceFitting.objects.create(
            session=self.session, model=self.model, grading_version=self.gv)
        self.lines = {
            sl: PieceFittingLine.objects.create(
                piece_fitting=self.pf, pom=self.pom, size_label=sl,
                valor_teoric=TEORICS[sl], valor_real=TEORICS[sl])
            for sl in ['S', 'M', 'L', 'XL']
        }
        self.factory = APIRequestFactory()

    def _rectifica(self, decisio, valor=26.0):
        """La cel·la de la talla BASE, mesurada diferent del teòric i amb un veredicte."""
        linia = self.lines['M']
        linia.valor_real = valor
        linia.decisio = decisio
        linia.save(update_fields=['valor_real', 'decisio'])
        return linia

    def _consolida(self):
        from fhort.fitting.services import consolidate_base_from_fitting
        return consolidate_base_from_fitting(self.pf, auth_user=self.user)


class VeredicteEsDesaTest(_BaseVeredicteTest):
    """F1 — el camp i el seu camí de desat."""

    def _patch(self, linia, cos):
        vista = PieceFittingLineViewSet.as_view({'patch': 'partial_update'})
        req = self.factory.patch('/', cos, format='json')
        force_authenticate(req, user=self.user)
        return vista(req, pk=linia.pk)

    def test_el_veredicte_es_desa_pel_mateix_PATCH_que_la_nota(self):
        """La nota ja hi anava; el veredicte no havia d'estrenar cap endpoint."""
        res = self._patch(self.lines['M'],
                          {'decisio': 'ADJUSTED', 'nota': 'puja 2 al pit'})
        self.assertEqual(res.status_code, 200)
        linia = PieceFittingLine.objects.get(pk=self.lines['M'].pk)
        self.assertEqual((linia.decisio, linia.nota), ('ADJUSTED', 'puja 2 al pit'))

    def test_el_veredicte_torna_al_payload_de_la_linia(self):
        """Sense això la graella no el pot repintar en tornar a obrir la sessió."""
        res = self._patch(self.lines['M'], {'decisio': 'REJECTED'})
        self.assertEqual(res.data['decisio'], 'REJECTED')

    def test_sense_decidir_NO_es_acceptada(self):
        """La distinció que fa que el camp serveixi de res: una cel·la que ningú no ha mirat
        no pot quedar igual que una que algú ha donat per bona. Si el default fos el primer
        choice, obrir un fitting i tancar-lo sense tocar res deixaria tota la graella
        «acceptada» sense que ningú hi hagués dit res."""
        self.assertEqual(self.lines['S'].decisio, '')
        self.assertNotEqual(self.lines['S'].decisio,
                            PieceFittingLine.DECISIO_ACCEPTED)

    def test_es_pot_desdir(self):
        """Tornar a clicar el veredicte actiu el treu (el front hi compta): decidir i
        desdir-se han de costar el mateix."""
        self._patch(self.lines['M'], {'decisio': 'ACCEPTED'})
        self._patch(self.lines['M'], {'decisio': ''})
        self.assertEqual(PieceFittingLine.objects.get(pk=self.lines['M'].pk).decisio, '')


class RebuigNoSembraTest(_BaseVeredicteTest):
    """🔴 LA LLEI D-31.21 pel camí 1: la consolidació a `BaseMeasurement`."""

    def test_una_linia_REJECTED_no_arriba_a_la_mesura_base(self):
        self._rectifica(PieceFittingLine.DECISIO_REJECTED)
        consolidades = self._consolida()

        self.assertEqual(consolidades, [], 'un rebuig ha sembrat')
        self.assertFalse(
            BaseMeasurement.objects.filter(model=self.model, pom=self.pom).exists(),
            'el rebuig ha escrit una mesura base que ningú no ha donat per bona')

    def test_pero_la_linia_REJECTED_segueix_desada_i_visible(self):
        """El rebuig NO és un esborrat: la xifra que la modista ha pres es queda, i el full
        que va a la sala l'ha de poder ensenyar amb el seu RJ al costat."""
        self._rectifica(PieceFittingLine.DECISIO_REJECTED)
        self._consolida()
        linia = PieceFittingLine.objects.get(pk=self.lines['M'].pk)
        self.assertEqual(linia.valor_real, 26.0)
        self.assertEqual(linia.decisio, PieceFittingLine.DECISIO_REJECTED)

    def test_una_ACCEPTED_si_que_sembra(self):
        """La cara B, i la que evita que el filtre sigui una regressió."""
        self._rectifica(PieceFittingLine.DECISIO_ACCEPTED)
        consolidades = self._consolida()

        self.assertEqual(len(consolidades), 1)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        self.assertEqual((bm.base_value_cm, bm.origen), (26.0, 'FITTED'))

    def test_una_ADJUSTED_si_que_sembra(self):
        """ADJUSTED és «s'ha rectificat i el valor rectificat val»: és justament el cas que
        MÉS ha de sembrar, perquè el número nou és la feina del fitting."""
        self._rectifica(PieceFittingLine.DECISIO_ADJUSTED)
        self.assertEqual(len(self._consolida()), 1)

    def test_una_cel_la_SENSE_decidir_segueix_sembrant(self):
        """El filtre és NOMÉS per al rebuig. Si el buit no sembrés, aquest camp hauria
        trencat en silenci tot el que hi havia abans que existís: cap de les 205 línies
        vives de staging té veredicte."""
        self._rectifica('')
        self.assertEqual(len(self._consolida()), 1)

    def test_el_rebuig_d_una_germana_no_atura_les_altres(self):
        """El filtre és per LÍNIA, no per peça: rebutjar una presa no pot fer desaparèixer
        la feina de les altres."""
        altre_pom = POMMaster.objects.create(codi_client='P2', nom_client='Cintura')
        PieceFittingLine.objects.create(
            piece_fitting=self.pf, pom=altre_pom, size_label='M',
            valor_teoric=50.0, valor_real=55.0,
            decisio=PieceFittingLine.DECISIO_ACCEPTED)
        self._rectifica(PieceFittingLine.DECISIO_REJECTED)

        consolidades = self._consolida()
        self.assertEqual([c.pom_id for c in consolidades], [altre_pom.id])


class RebuigNoPropagaTest(_BaseVeredicteTest):
    """🔴 LA LLEI D-31.21 pel camí 2: l'ancoratge en temps d'edició."""

    def _propagar(self, linia, valor_real):
        vista = PieceFittingLineViewSet.as_view({'post': 'propagar'})
        req = self.factory.post('/propagar/', {'valor_real': valor_real}, format='json')
        force_authenticate(req, user=self.user)
        return vista(req, pk=linia.pk)

    def _reals(self):
        return {sl: PieceFittingLine.objects.get(pk=self.lines[sl].pk).valor_real
                for sl in TEORICS}

    def test_una_linia_REJECTED_no_escampa_el_seu_delta_a_les_germanes_de_talla(self):
        linia = self.lines['M']
        linia.decisio = PieceFittingLine.DECISIO_REJECTED
        linia.save(update_fields=['decisio'])

        res = self._propagar(linia, 26.0)

        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['propagat'])
        self.assertEqual(res.data['motiu'], 'linia_rebutjada')
        reals = self._reals()
        self.assertEqual({sl: reals[sl] for sl in ('S', 'L', 'XL')},
                         {'S': 10.0, 'L': 30.0, 'XL': 40.0})

    def test_pero_la_cel_la_ancorada_es_desa_igual(self):
        """Desar i decidir són gestos separats. Que el delta no viatgi no vol dir que el
        número que la modista acaba d'escriure s'evapori de la pantalla."""
        linia = self.lines['M']
        linia.decisio = PieceFittingLine.DECISIO_REJECTED
        linia.save(update_fields=['decisio'])

        self._propagar(linia, 26.0)

        self.assertEqual(PieceFittingLine.objects.get(pk=linia.pk).valor_real, 26.0)

    def test_sense_rebuig_la_propagacio_segueix_funcionant(self):
        """Cara B: el guard nou no pot haver tapat el camí normal (règim LINEAR, +2)."""
        res = self._propagar(self.lines['M'], 26.0)
        self.assertTrue(res.data['propagat'])
        self.assertNotEqual(self._reals()['L'], 30.0)


class OrigenAlPayloadTest(_BaseVeredicteTest):
    """F2 — la pantalla ha de poder distingir la germana moguda pel sistema de la que ningú
    no ha tocat, i C3 ja havia construït amb què: `origen='DERIVAT'`."""

    def _payload(self):
        from fhort.fitting.serializers import PieceFittingGridSerializer
        return PieceFittingGridSerializer(self.pf).data['lines']

    def test_cada_linia_diu_l_origen_de_la_seva_mesura_base(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=20.0, origen='FITTED')
        origens = {f['size_label']: f['origen'] for f in self._payload()}
        self.assertEqual(origens['M'], 'FITTED')

    def test_una_germana_DERIVADA_es_pot_etiquetar(self):
        """El cas que motiva F2: l'exterior el mesura algú i el folre el mou el sistema. Sense
        `origen` al payload, les dues files es veurien igual i la pantalla no podria dir quina
        xifra ha mesurat una persona."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=20.0,
            capa='exterior', origen='FITTED')
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=18.0,
            capa='folre', origen='DERIVAT')
        PieceFittingLine.objects.create(
            piece_fitting=self.pf, pom=self.pom, size_label='M',
            valor_teoric=18.0, valor_real=18.0, capa='folre')

        per_capa = {(f['size_label'], f['capa']): f['origen'] for f in self._payload()}
        self.assertEqual(per_capa[('M', 'exterior')], 'FITTED')
        self.assertEqual(per_capa[('M', 'folre')], 'DERIVAT')

    def test_el_payload_tambe_porta_el_veredicte(self):
        """Perquè D-31.21 es pugui aplicar a la germana cal veure el seu veredicte, no només
        el de la fila que s'està mirant."""
        self._rectifica(PieceFittingLine.DECISIO_REJECTED)
        decisions = {f['size_label']: f['decisio'] for f in self._payload()}
        self.assertEqual(decisions['M'], 'REJECTED')
        self.assertEqual(decisions['S'], '')
