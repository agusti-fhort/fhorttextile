"""E1 · QA DE PUNTA A PUNTA — el cicle sencer dels dos passos.

    presa de 5 talles → desviació → decidir NOMÉS a la base → close → propagar
    → la taula de la fitxa (E1/B2) amb els tres valors coherents

Substrat: brief E1 + `docs/diagnosis/DIAGNOSI_E1_MESURA_ESCALAT.md`.

🚨 PER QUÈ AQUEST BANC EXISTEIX I NO N'HI HA PROU AMB ELS DE CADA PEÇA. Cada bloc d'E1 té el
seu banc i tots són verds, i tanmateix el defecte que E1 arregla **només es veu en la junta**:
el pas 1 escrivia la corba, el pas 2 clonava aquella corba com a teòric, i cada peça per
separat feia exactament el que deia. La desviació sortia zero i cap banc de cap peça ho podia
dir. La llei de S42 aplicada aquí: *el guard ha d'arribar a la JUNTA, no a les peces.*

Topologia: germana del banc QA viu (model 1380 «QA-F1-GARMENT»), amb el MATEIX POM viu a la
mare i a la peça `02` amb la mateixa `(capa, instancia)` i **regles DIVERGENTS** — sense la
divergència, la contramostra de Q1-bis passaria amb el defecte viu.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting import services
from fhort.fitting.escalat_presa_views import EscalatPresaView
from fhort.fitting.models import (
    FittingSession, GradedSpec, GradingVersion, PieceFitting, PieceFittingLine, SizeFitting,
)
from fhort.fitting.views import PieceFittingLineViewSet
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

RUN = ['XS', 'S', 'M', 'L', 'XL']
BASE = 'M'
MARE = ''
SEGONA = '02'
BASE_MARE = 50.0
BASE_02 = 30.0
D_MARE = 2.0        # la mare gradua de 2 en 2…
D_02 = 1.0          # …i la 02 d'1 en 1. LA DIVERGÈNCIA ÉS EL BANC.


class CicleE1Test(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tester_e2e')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        ss = SizeSystem.objects.create(codi='SS_E2E', nom='SS e2e', base_unit='ALPHA')
        self.talles = {et: SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
                       for i, et in enumerate(RUN, start=1)}
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='QA-E1-CICLE', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='·'.join(RUN), base_size_label=BASE,
            size_system=ss)

        for garment, val, delta in ((MARE, BASE_MARE, D_MARE), (SEGONA, BASE_02, D_02)):
            BaseMeasurement.objects.create(model=self.model, pom=self.pom, garment=garment,
                                           base_value_cm=val, is_active=True)
            # Regla RESIDENT per peça: `_load_grading_rules_per_garment` + `_regla_de` les
            # reparteixen, i és el que la contramostra de Q1-bis vigila.
            # `ModelGradingRule` és RESIDENT al model i no porta `talla_base`: la base la diu
            # `model.base_size_label` i el break es resol per etiqueta contra el run
            # (v. la capçalera del model, `models_app/models.py:1116`).
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, garment=garment,
                logica='LINEAR', increment=delta, increment_base=delta,
                origen='MANUAL', actiu=True)

        sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-E2E-1', 'tipus': 'PRINCIPAL', 'creat_per': self.profile})
        self.sf = sf
        self.factory = APIRequestFactory()
        self.presa_view = EscalatPresaView.as_view()
        self.patch_view = PieceFittingLineViewSet.as_view({'patch': 'partial_update'})

    # ── passos ──────────────────────────────────────────────────────────────────────────
    def _propaga(self):
        """L'acte conscient: genera/regenera la corba des de base + regla."""
        from fhort.pom.services import generate_graded_specs
        return generate_graded_specs(self.sf.id)

    def _obre_presa(self):
        gv = GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).first()
        sessio = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 17), estat='Oberta')
        pf, _n = services.create_piece_fitting(sessio.id, self.model.id,
                                              created_by_id=self.profile.pk)
        self.assertIsNotNone(gv)
        return pf

    def _anota(self, talla, valor, garment=MARE):
        req = self.factory.post('/presa/', {'pom_id': self.pom.id, 'talla': talla,
                                            'valor': valor, 'garment': garment}, format='json')
        force_authenticate(req, user=self.user)
        return self.presa_view(req, model_id=self.model.id)

    def _decideix(self, linia, veredicte):
        req = self.factory.patch('/', {'decisio': veredicte}, format='json')
        force_authenticate(req, user=self.user)
        return self.patch_view(req, pk=linia.pk)

    def _linia(self, pf, talla, garment=MARE):
        return PieceFittingLine.objects.get(piece_fitting=pf, pom=self.pom,
                                            size_label=talla, garment=garment)

    def _corba(self, garment=MARE):
        gv = GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).first()
        return {s.size_label: s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom,
                                                   garment=garment)}

    # ── EL CICLE ────────────────────────────────────────────────────────────────────────
    def test_cicle_complet_presa_decisio_close_propagacio(self):
        # ① La corba de sortida, i que CADA PEÇA GRADUA AMB LA SEVA LLEI (contramostra Q1-bis).
        self._propaga()
        self.assertEqual(self._corba(MARE),
                         {'XS': 46.0, 'S': 48.0, 'M': 50.0, 'L': 52.0, 'XL': 54.0})
        self.assertEqual(self._corba(SEGONA),
                         {'XS': 28.0, 'S': 29.0, 'M': 30.0, 'L': 31.0, 'XL': 32.0})

        # ② S'obre la presa i arriben les peces físiques: es mesuren LES CINC TALLES.
        pf = self._obre_presa()
        arribades = {'XS': 46.5, 'S': 48.2, 'M': 51.0, 'L': 52.3, 'XL': 54.9}
        for talla, valor in arribades.items():
            self.assertEqual(self._anota(talla, valor).status_code, 200, talla)

        # ③ LA DESVIACIÓ ES VEU (R1) — i és la prova que el pas 1 NO ha mogut el referent.
        #    Abans d'E1 aquesta llista era cinc zeros: la cel·la escrivia la corba i el teòric
        #    es re-derivava del mateix número que s'acabava d'anotar.
        req = self.factory.get('/presa/')
        force_authenticate(req, user=self.user)
        preses = self.presa_view(req, model_id=self.model.id).data
        from fhort.pom.identitat import clau_mesura
        clau = clau_mesura(self.pom.id, 'exterior', '', MARE)
        desviacions = {t: preses['preses'][f'{clau}:{t}']['desviacio'] for t in RUN}
        self.assertEqual(desviacions, {'XS': 0.5, 'S': 0.2, 'M': 1.0, 'L': 0.3, 'XL': 0.9})
        self.assertNotIn(0.0, desviacions.values())
        self.assertEqual(preses['resum']['n_preses'], 5)

        # ④ LA CORBA NO S'HA MOGUT: cinc preses i el domini intacte.
        self.assertEqual(self._corba(MARE),
                         {'XS': 46.0, 'S': 48.0, 'M': 50.0, 'L': 52.0, 'XL': 54.0})
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom,
                                        garment=MARE).base_value_cm, BASE_MARE)

        # ⑤ ES DECIDEIX NOMÉS A LA BASE (R2). Les altres talles no s'accepten.
        self.assertEqual(self._decideix(self._linia(pf, 'L'), 'ACCEPTED').status_code, 400)
        self.assertEqual(self._decideix(self._linia(pf, BASE), 'ACCEPTED').status_code, 200)

        # ⑥ CLOSE: consolida NOMÉS la base, i NOMÉS la que s'ha decidit.
        services.close_piece_fitting(pf.pk, user_profile_id=self.profile.pk)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom,
                                        garment=MARE).base_value_cm, 51.0)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom,
                                        garment=SEGONA).base_value_cm, BASE_02)

        # ⑦ PROPAGAR: la corba nova surt de la base acceptada AMB LA LLEI DE CADA PEÇA.
        self._propaga()
        self.assertEqual(self._corba(MARE),
                         {'XS': 47.0, 'S': 49.0, 'M': 51.0, 'L': 53.0, 'XL': 55.0})
        # La 02 no s'ha tocat i segueix amb el SEU delta d'1: si la mare li hagués aplicat la
        # seva llei, aquí hi hauria 28/29/30/31/32 desplaçats de 2 en 2.
        self.assertEqual(self._corba(SEGONA),
                         {'XS': 28.0, 'S': 29.0, 'M': 30.0, 'L': 31.0, 'XL': 32.0})

    def test_la_presa_SOBREVIU_al_close_i_a_la_propagacio(self):
        """El full de la fitxa (E1/B2) es fa DESPRÉS de decidir: si el cicle esborrés les
        preses, la taula de teòrica·arribada·final es quedaria sense la columna del mig."""
        self._propaga()
        pf = self._obre_presa()
        self._anota('L', 52.3)
        self._decideix(self._linia(pf, BASE), 'ACCEPTED')
        services.close_piece_fitting(pf.pk, user_profile_id=self.profile.pk)
        self._propaga()
        self.assertEqual(self._linia(pf, 'L').valor_real, 52.3)
        self.assertEqual(self._linia(pf, 'L').valor_teoric, 52.0)   # el contracte no es mou

    def test_una_presa_REBUTJADA_no_consolida_i_es_veu_igual(self):
        self._propaga()
        pf = self._obre_presa()
        self._anota(BASE, 44.0)
        self._decideix(self._linia(pf, BASE), 'REJECTED')
        services.close_piece_fitting(pf.pk, user_profile_id=self.profile.pk)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom,
                                        garment=MARE).base_value_cm, BASE_MARE)
        self.assertEqual(self._linia(pf, BASE).valor_real, 44.0)    # la presa NO desapareix

    def test_la_presa_es_PAUSABLE_un_client_nou_la_rehidrata_sencera(self):
        """El flux passa entre el taller i el despatx, potser un altre dia: tot el que la
        pantalla necessita per reprendre ha d'estar al SERVIDOR, mai en estat de client."""
        self._propaga()
        self._obre_presa()
        self._anota('L', 52.3)
        self._anota('XL', 54.9)
        req = self.factory.get('/presa/')       # «client nou»: cap estat previ
        force_authenticate(req, user=self.user)
        d = self.presa_view(req, model_id=self.model.id).data
        self.assertTrue(d['presa_oberta'])
        self.assertEqual(d['resum']['n_preses'], 2)
        self.assertEqual(sorted(d['resum']['talles_amb_presa']), ['L', 'XL'])
        self.assertEqual(d['session']['data'], '2026-08-17')
        self.assertEqual(d['resum']['pendents_base'], 2)     # mare + 02, cap decidida
