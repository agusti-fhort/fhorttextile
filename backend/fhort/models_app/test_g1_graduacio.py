"""LA GRADUACIÓ S'INFORMA PEL SEU GEST, I MESURES DIU NOMÉS EL QUE EL MODEL DIU.

Contracte final (Agus, 31/07, correcció de rumb): el gest de graduar viu a MESURES —el botó
«Graduació» obre el pas 4 del wizard com a overlay— i «Usar aquest joc» escriu pel mecanisme
vigent (`update-step2`: assignar el ruleset + materialitzar). Escalat torna a ser la seva
pestanya de sempre.

El que aquests tests defensen, i que ve del QA del model 1302:
  · **BD neta = taula neta.** El payload de Mesures porta les regles DEL MODEL i prou. Mai la
    proposta del catàleg, mai fusionada per fallback. Un model creat sense graduació no pot
    ensenyar la regla d'un altre.
  · **Desar mesures no escriu regles.** El camí que fabricava residents amb `logica||'LINEAR'`
    per a cada fila no torna: sense ell, desar la taula donava graduació a qui no en tenia.
  · **Sense regla no es propaga**, i `te_regles` és el senyal que ho diu abans (perquè el front
    pugui obrir el pas de Graduació en lloc d'ensenyar un 400 mut).

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.models_app.views import (generate_grading_view, grading_status_view,
                                    measurements_table_view, set_measurements_view,
                                    update_model_step2)
from fhort.pom.models import (GarmentType, GradingRule, GradingRuleSet, POMMaster,
                              SizeDefinition, SizeSystem)


class _Base(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='grad')
        self.factory = APIRequestFactory()
        self.ss = SizeSystem.objects.create(codi='SS_G', nom='SS G', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.talla_base = SizeDefinition.objects.get(size_system=self.ss, etiqueta='M')
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest width')

    def _ruleset(self, nom='RS', increment=2.0):
        rs = GradingRuleSet.objects.create(nom=nom, size_system=self.ss, actiu=True)
        GradingRule.objects.create(rule_set=rs, pom=self.pom, talla_base=self.talla_base,
                                   logica='LINEAR', increment=increment,
                                   increment_base=increment, actiu=True)
        return rs

    def _model(self, codi='TST-G', *, rule_set=None):
        m = Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=1, nom_prenda='T',
            size_system=self.ss, size_run_model='S·M·L', base_size_label='M',
            grading_rule_set=rule_set)
        BaseMeasurement.objects.create(model=m, pom=self.pom, base_value_cm=100.0)
        return m

    def _gti(self, code, rs):
        """Un item amb ruleset al catàleg: el muntatge exacte del model 1302."""
        from fhort.tasks.models import GarmentTypeItem
        gt = GarmentType.objects.create(codi_client=code, nom_client=code, grup='TOP')
        return GarmentTypeItem.objects.create(code=code, name='Item', garment_type=gt,
                                              grading_rule_set=rs)

    def GET(self, view, mid):
        r = self.factory.get('/x'); force_authenticate(r, user=self.user); return view(r, mid)

    def POST(self, view, mid, body=None):
        r = self.factory.post('/x', body or {}, format='json')
        force_authenticate(r, user=self.user); return view(r, mid)

    def PATCH(self, view, mid, body):
        r = self.factory.patch('/x', body, format='json')
        force_authenticate(r, user=self.user); return view(r, mid)


class MesuresDiuNomesElQueElModelDiuTest(_Base):
    """BD neta = taula neta. La lliçó del 1302, fixada."""

    def test_un_model_sense_graduacio_no_ensenya_la_regla_del_seu_item(self):
        rs = self._ruleset('RS de litem')
        model = self._model()
        model.garment_type_item = self._gti('it1', rs)
        model.save(update_fields=['garment_type_item'])

        fila = self.GET(measurements_table_view, model.id).data['rows'][0]

        self.assertIsNone(fila['logica'], 'Mesures ha pintat un règim que el model no té')
        self.assertIsNone(fila['increment_base'])
        self.assertIsNone(fila['increment_break'])
        self.assertIsNone(fila['talla_break_label'])

    def test_un_model_amb_regles_SI_que_les_ensenya(self):
        model = self._model(rule_set=self._ruleset('RS del model'))

        fila = self.GET(measurements_table_view, model.id).data['rows'][0]

        self.assertEqual(fila['logica'], 'LINEAR')
        self.assertEqual(fila['increment_base'], 2.0)

    def test_mirar_la_taula_no_escriu_res(self):
        rs = self._ruleset()
        model = self._model()
        model.garment_type_item = self._gti('it2', rs)
        model.save(update_fields=['garment_type_item'])

        self.GET(measurements_table_view, model.id)

        model.refresh_from_db()
        self.assertIsNone(model.grading_rule_set_id)
        self.assertEqual(ModelGradingRule.objects.filter(model=model).count(), 0)


class UsarAquestJocEscriuPelMecanismeVigentTest(_Base):
    """«Usar aquest joc» = `update-step2`, que és com el wizard ho ha fet sempre."""

    def test_el_cicle_sencer_del_gest(self):
        rs = self._ruleset('RS triat')
        model = self._model()

        # 1. abans: ni regles ni columnes
        self.assertFalse(self.GET(grading_status_view, model.id).data['te_regles'])
        self.assertIsNone(self.GET(measurements_table_view, model.id).data['rows'][0]['logica'])

        # 2. propagar encara no pot
        self.assertEqual(
            self.POST(generate_grading_view, model.id, {'new_version': True}).status_code, 400)

        # 3. «Usar aquest joc» → assigna i materialitza
        r = self.PATCH(update_model_step2, model.id, {'grading_rule_set_id': rs.id})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(ModelGradingRule.objects.filter(model=model, actiu=True).count(), 1)

        # 4. ara les columnes de Mesures tenen què ensenyar, i propagar ja pot
        self.assertEqual(self.GET(measurements_table_view, model.id).data['rows'][0]['logica'],
                         'LINEAR')
        self.assertTrue(self.GET(grading_status_view, model.id).data['te_regles'])
        self.assertNotEqual(
            self.POST(generate_grading_view, model.id, {'new_version': True}).status_code, 400)


class DesarMesuresNoFabricaReglesTest(_Base):
    """L'altra meitat del bug del 1302: el payload de Mesures ja no porta `rules`."""

    def test_desar_mesures_dun_model_sense_graduacio_no_len_inventa_cap(self):
        rs = self._ruleset()
        model = self._model()
        model.garment_type_item = self._gti('it3', rs)
        model.save(update_fields=['garment_type_item'])

        r = self.POST(set_measurements_view, model.id, {
            'measurements': [{'pom_id': self.pom.id, 'base_value_cm': 101.0}],
            'keep_pom_ids': [self.pom.id],
        })

        self.assertEqual(r.status_code, 201, getattr(r, 'data', None))
        self.assertEqual(r.data['updated'], 1, "la mesura sí que s'ha de desar")
        self.assertEqual(ModelGradingRule.objects.filter(model=model).count(), 0,
                         'desar mesures ha fabricat una regla que ningú no ha informat')


class SenseGraduacioNoPetaResTest(_Base):
    """`grading_rule_set=NULL` i zero residents és un ESTAT VÀLID: un model amb només talla
    base és complet per a la seva fase, i cap superfície pot petar per això."""

    def test_les_dues_superficies_responen_200(self):
        model = self._model()
        for view in (measurements_table_view, grading_status_view):
            with self.subTest(view=view.__name__):
                self.assertEqual(self.GET(view, model.id).status_code, 200)

    def test_la_base_hi_es_encara_que_no_sapiga_graduar(self):
        model = self._model()

        d = self.GET(measurements_table_view, model.id).data

        self.assertEqual(len(d['rows']), 1)
        self.assertEqual(d['rows'][0]['base_value_cm'], 100.0)
        self.assertIsNone(d['rows'][0]['logica'])
