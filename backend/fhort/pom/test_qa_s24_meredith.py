"""QA de tancament S24 — geometria real del cas Meredith/BRW (regressió).

Document de 5 talles (XXS-L) sobre un sistema de 8 (ALPHA_EU_W). Valors reals extrets de
media/fhort/import_sessions/2026/07/BRW_POP_SIZE_SET_depurat.xlsx.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.size_map_views import size_map_grading_preview_view, size_map_create_view

RUN_SISTEMA = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
# Valors REALS del document (21 POMs, 5 talles), inlinats perquè el test sigui autònom.
TAULA = [
    {'pom_codi_client': 'A', 'descripcio': '1/2 Chest width (armpit to armpit)',
     'valors': {'XXS': 41, 'XS': 43, 'S': 46, 'M': 49, 'L': 52}},
    {'pom_codi_client': 'D', 'descripcio': '1/2 Bottom width',
     'valors': {'XXS': 49, 'XS': 51, 'S': 54, 'M': 57, 'L': 60}},
    {'pom_codi_client': 'E2', 'descripcio': 'Thorax width in front',
     'valors': {'XXS': 30.5, 'XS': 31.5, 'S': 33, 'M': 34.5, 'L': 36}},
    {'pom_codi_client': 'E3', 'descripcio': 'Back width',
     'valors': {'XXS': 30.5, 'XS': 31.5, 'S': 33, 'M': 34.5, 'L': 36}},
    {'pom_codi_client': 'E', 'descripcio': 'Shoulder to shoulder',
     'valors': {'XXS': 32.5, 'XS': 33.5, 'S': 35, 'M': 36.5, 'L': 38}},
    {'pom_codi_client': 'E5', 'descripcio': 'Shoulder drop',
     'valors': {'XXS': 2, 'XS': 2, 'S': 2, 'M': 2, 'L': 2}},
    {'pom_codi_client': 'E1', 'descripcio': 'Shoulder seam',
     'valors': {'XXS': 8.35, 'XS': 8.6, 'S': 9, 'M': 9.4, 'L': 9.8}},
    {'pom_codi_client': 'E4', 'descripcio': 'Shoulder forward',
     'valors': {'XXS': 1.5, 'XS': 1.5, 'S': 1.5, 'M': 1.5, 'L': 1.5}},
    {'pom_codi_client': 'EK', 'descripcio': 'Neck width (seam to seam)',
     'valors': {'XXS': 15.75, 'XS': 16.25, 'S': 17, 'M': 17.75, 'L': 18.5}},
    {'pom_codi_client': 'EK1', 'descripcio': 'Front neckline drop',
     'valors': {'XXS': 7.35, 'XS': 7.6, 'S': 8, 'M': 8.4, 'L': 8.8}},
    {'pom_codi_client': 'EK2', 'descripcio': 'Back neckline drop',
     'valors': {'XXS': 2.5, 'XS': 2.5, 'S': 2.5, 'M': 2.5, 'L': 2.5}},
    {'pom_codi_client': 'F', 'descripcio': 'Centre front length at CF',
     'valors': {'XXS': 52, 'XS': 53, 'S': 54, 'M': 55, 'L': 56}},
    {'pom_codi_client': 'FF', 'descripcio': 'Centre back length at CB',
     'valors': {'XXS': 49, 'XS': 50, 'S': 51, 'M': 52, 'L': 53}},
    {'pom_codi_client': 'SF', 'descripcio': 'Armhole depth',
     'valors': {'XXS': 19.8, 'XS': 20.5, 'S': 21.5, 'M': 22.5, 'L': 23.5}},
    {'pom_codi_client': 'S', 'descripcio': 'Front armhole along seam',
     'valors': {'XXS': 21.3, 'XS': 22, 'S': 23, 'M': 24, 'L': 25}},
    {'pom_codi_client': 'S2', 'descripcio': 'Back armhole along seam',
     'valors': {'XXS': 22.3, 'XS': 23, 'S': 24, 'M': 25, 'L': 26}},
    {'pom_codi_client': 'I', 'descripcio': 'Sleeve length',
     'valors': {'XXS': 59.5, 'XS': 60.5, 'S': 61.5, 'M': 62.5, 'L': 63.5}},
    {'pom_codi_client': 'J', 'descripcio': '1/2 Bicep width',
     'valors': {'XXS': 15.1, 'XS': 15.7, 'S': 16.5, 'M': 17.3, 'L': 18.1}},
    {'pom_codi_client': 'J1', 'descripcio': 'Sleeve opening',
     'valors': {'XXS': 8.2, 'XS': 8.5, 'S': 9, 'M': 9.5, 'L': 10}},
    {'pom_codi_client': 'J2', 'descripcio': '1/2 Elbow width',
     'valors': {'XXS': 15.1, 'XS': 15.7, 'S': 16.5, 'M': 17.3, 'L': 18.1}},
    {'pom_codi_client': 'J3', 'descripcio': 'Cuff height',
     'valors': {'XXS': 0.7, 'XS': 0.7, 'S': 0.7, 'M': 0.7, 'L': 0.7}},
]


class QaS24Test(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'QA S24'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'QA1'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.pom.models import SizeSystem, SizeDefinition, POMMaster, Target
        self.user = get_user_model().objects.create(username='qa-s24')
        p, _ = UserProfile.objects.get_or_create(user=self.user)
        p.rol_nom = 'admin'
        p.permisos = {'grant': ['configure']}
        p.save()
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.target = Target.objects.create(codi='W', nom_en='Woman')
        self.ss = SizeSystem.objects.create(codi='ALPHA_EU_W_QA', nom='Alpha EU W',
                                            base_unit='ALPHA', actiu=True)
        self.ss.targets.add(self.target)
        for i, e in enumerate(RUN_SISTEMA):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=e, ordre=i + 1)
        for row in TAULA:
            POMMaster.objects.get_or_create(
                codi_client=row['pom_codi_client'],
                defaults={'nom_client': row['descripcio'] or row['pom_codi_client']})

    def _post(self, view, url, payload):
        req = APIRequestFactory().post(url, payload, format='json')
        force_authenticate(req, user=self.user)
        return view(req)

    def test_Q1_preview_no_bloqueja_i_deriva_el_break_a_l_extrem_petit(self):
        r = self._post(size_map_grading_preview_view, '/api/v1/size-map/grading-preview/',
                       {'size_system_id': self.ss.id, 'base_size': 'S', 'taula': TAULA})
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        # (1) El referent és el run del DOCUMENT, no el del sistema.
        self.assertEqual(r.data['run'], ['XXS', 'XS', 'S', 'M', 'L'])
        # (2) CAP fila incompleta (abans: totes, per XL/XXL/3XL absents del document).
        incompletes = [x for x in r.data['results'] if x['incompleta']]
        self.assertEqual(incompletes, [], f"{len(incompletes)} files marcades incompletes")
        self.assertEqual(len(r.data['results']), len(TAULA))
        # (3) Break a l'EXTREM PETIT, derivat dels valors reals: A = 41·43·46·49·52 amb base S
        #     → deltes XXS:2 · XS:3 · M:3 · L:3 → base=2, break=3 a partir de XS.
        a = next(x for x in r.data['results'] if x['pom_codi_client'] == 'A')
        self.assertEqual(a['logica_detectada'], 'LINEAR')
        self.assertEqual(a['increment_base'], 2.0)
        self.assertEqual(a['increment_break'], 3.0)
        self.assertEqual(a['talla_break_label'], 'XS')
        # (4) POM pla (E5 = 2 a totes les talles) → FIXED, sense break.
        e5 = next(x for x in r.data['results'] if x['pom_codi_client'] == 'E5')
        self.assertEqual(e5['logica_detectada'], 'FIXED')
        self.assertIsNone(e5['increment_break'])

    def test_Q1_create_persisteix_el_break_i_avisa_de_l_extrapolacio(self):
        prev = self._post(size_map_grading_preview_view, '/api/v1/size-map/grading-preview/',
                          {'size_system_id': self.ss.id, 'base_size': 'S', 'taula': TAULA})
        grading = [{'pom_id': x['pom_id'], 'codi': x['pom_codi_client'],
                    'logica': x['logica_detectada'], 'increment': x['increment'],
                    'valors_step': x['valors_step'], 'incompleta': False, 'missing_sizes': []}
                   for x in prev.data['results'] if x['pom_id']]
        r = self._post(size_map_create_view, '/api/v1/size-map/create/', {
            'accio': 'REUTILITZAR', 'size_system_id': self.ss.id, 'target_codi': 'W',
            'base_unit': 'ALPHA', 'base_size': 'S', 'customer_codi': '',
            'talles': [], 'grading': grading, 'perfils': [],
            'doc_run': prev.data['run'],
        })
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        self.assertEqual(r.data['rules_count'], len(grading))
        # El break persistit es localitza sobre el run del DOCUMENT.
        from fhort.pom.models import GradingRule
        rule = GradingRule.objects.get(rule_set_id=r.data['grading_rule_set_id'],
                                       pom__codi_client='A')
        self.assertEqual(float(rule.increment_base), 2.0)
        self.assertEqual(float(rule.increment_break), 3.0)
        self.assertEqual(rule.talla_break_label, 'XS')
        self.assertEqual(rule.talla_base.etiqueta, 'S')
        # 🚩2 — avís d'extrapolació: el document cobria 5 de 8 talles.
        self.assertIsNotNone(r.data['extrapolacio'])
        self.assertEqual(r.data['extrapolacio']['talles'], ['XL', 'XXL', '3XL'])

    def test_check_d_talla_desconeguda_es_400(self):
        taula = [dict(TAULA[0])]
        taula[0]['valors'] = dict(taula[0]['valors'], **{'5XL': 99})
        r = self._post(size_map_grading_preview_view, '/api/v1/size-map/grading-preview/',
                       {'size_system_id': self.ss.id, 'base_size': 'S', 'taula': taula})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['etiquetes_desconegudes'], ['5XL'])

    def test_forat_intern_real_segueix_bloquejant(self):
        taula = [dict(TAULA[0]), dict(TAULA[1])]
        taula[0]['valors'] = dict(taula[0]['valors'])
        taula[0]['valors']['M'] = None          # forat DINS del run del document
        r = self._post(size_map_grading_preview_view, '/api/v1/size-map/grading-preview/',
                       {'size_system_id': self.ss.id, 'base_size': 'S', 'taula': taula})
        self.assertEqual(r.status_code, 200)
        a = next(x for x in r.data['results'] if x['pom_codi_client'] == 'A')
        self.assertTrue(a['incompleta'])
        self.assertEqual(a['missing_sizes'], ['M'])

    def test_Q3_import_de_fitxa_no_fabrica_el_break_amb_run_de_model_estret(self):
        """Bug 166: model amb run XS·S·L i document dens XXS-L. El referent és el DOCUMENT."""
        from fhort.pom.models import POMMaster
        from fhort.pom.grading_utils import derive_rules_from_fitxa
        pom_a = POMMaster.objects.get(codi_client='A')
        valors = {pom_a.id: {'XXS': 41, 'XS': 43, 'S': 46, 'M': 49, 'L': 52}}
        avisos, bloqueigs = [], []
        specs = derive_rules_from_fitxa(
            run_document=['XXS', 'XS', 'S', 'M', 'L'], base_size='S', valors=valors,
            confirmed_pom_ids=[pom_a.id], size_system=self.ss,
            avisos=avisos, bloqueigs=bloqueigs)
        self.assertEqual(bloqueigs, [])
        self.assertEqual(len(specs), 1)
        # ABANS (referent = run del model XS·S·L): base=3, break=6 (=2×), label='L'.
        self.assertEqual(specs[0]['increment_base'], 2.0)
        self.assertEqual(specs[0]['increment_break'], 3.0)
        self.assertEqual(specs[0]['talla_break_label'], 'XS')

    def test_Q3_import_de_fitxa_bloqueja_el_forat_intern(self):
        from fhort.pom.models import POMMaster
        from fhort.pom.grading_utils import derive_rules_from_fitxa
        pom_a = POMMaster.objects.get(codi_client='A')
        valors = {pom_a.id: {'XXS': 41, 'XS': 43, 'S': 46, 'L': 52}}   # falta M
        avisos, bloqueigs = [], []
        specs = derive_rules_from_fitxa(
            run_document=['XXS', 'XS', 'S', 'M', 'L'], base_size='S', valors=valors,
            confirmed_pom_ids=[pom_a.id], size_system=self.ss,
            avisos=avisos, bloqueigs=bloqueigs)
        self.assertEqual(specs, [])
        self.assertEqual(bloqueigs[0]['tipus'], 'fila_incompleta')
        self.assertEqual(bloqueigs[0]['missing_sizes'], ['M'])
