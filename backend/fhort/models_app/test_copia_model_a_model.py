"""Tests de la CÒPIA model→model (`/models/<dst>/copiar-de/<src>/`) — Sprint B · B2.

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

L'endpoint és el mirall de `materialize_poms_view` amb una font diferent (un altre MODEL en
comptes de l'ITEM). El que defensen aquests tests és exactament el que separa una còpia útil
d'una còpia mentidera:

  1. Bases COINCIDENTS → els valors viatgen amb `origen='COPIED'` (mai el `src.origen`
     verbatim: un MANUAL copiat afirmaria que algú va mesurar AQUEST model).
  2. Bases DIVERGENTS → guard P1 transposat: viatja la PERTINENÇA (fila TEMPLATE buida) i CAP
     valor, amb avís explícit. Sense això es reintrodueix el bug que P1 va corregir.
  3. Destí amb mesures pròpies → `copy_run` s'IGNORA amb avís (mai trepitjar el marc en què
     estan expressats els valors que el destí ja té).
  4. SOBIRANIA: una fila MANUAL del destí no es toca mai, ni tan sols amb un valor millor a
     l'origen; les intactes es compten a `skipped`.
  5. Els fitxers copiats neixen amb la VERSIÓ i el NOM del destí, no de l'origen.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelFitxer, ModelGradingRule
from fhort.models_app.views import copiar_de_model_view
from fhort.pom.models import (GarmentType, GradingRule, GradingRuleSet, POMMaster,
                              SizeDefinition, SizeSystem)
from fhort.tasks.models import GarmentTypeItem


class _BaseCopiaTest(TenantTestCase):
    PREFIX = 'CPY'

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
        self.user = get_user_model().objects.create(username=f'tec{self.PREFIX}')
        UserProfile.objects.get_or_create(user=self.user)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self._seq = 0

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _codi(self, base):
        return f'{self.PREFIX}_{base}'

    def _pom(self, codi):
        return POMMaster.objects.create(codi_client=self._codi(codi), nom_client=f'POM {codi}')

    def _item(self, code='blouse'):
        gt = GarmentType.objects.create(
            codi_client=self._codi('GT'), nom_client='Família de prova', grup='TOPS')
        return GarmentTypeItem.objects.create(
            garment_type=gt, code=self._codi(code), name='Item de prova')

    def _size_system(self, codi='SS', talles=('S', 'M', 'L')):
        ss = SizeSystem.objects.create(codi=self._codi(codi), nom=f'Sistema {codi}')
        for i, et in enumerate(talles):
            SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
        return ss

    def _model(self, **kw):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'{self.PREFIX}-M{self._seq}', codi_tenant='TST', any=2026,
            temporada='SS', sequencial=self._seq, created_by_id=self.user.profile.id, **kw)

    def _copiar(self, dst, src, body=None):
        req = APIRequestFactory().post(
            f'/api/v1/models/{dst.id}/copiar-de/{src.id}/', body or {}, format='json')
        force_authenticate(req, user=self.user)
        return copiar_de_model_view(req, dst.id, src.id)


class CopiaValorsTest(_BaseCopiaTest):
    """Què viatja i amb quin origen segons la talla base."""

    PREFIX = 'CPYV'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.ss = self._size_system()
        self.pom_a, self.pom_b = self._pom('A'), self._pom('B')
        self.src = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                               size_system=self.ss, size_run_model='S·M·L', base_size_label='M')
        BaseMeasurement.objects.create(model=self.src, pom=self.pom_a, base_value_cm=60.0,
                                       origen='MANUAL', is_key=True, ordre=0, nom_fitxa='A',
                                       tolerancia_minus='0.50', tolerancia_plus='0.50',
                                       notes='Confirmat pel proveïdor en AQUEST model')
        BaseMeasurement.objects.create(model=self.src, pom=self.pom_b, base_value_cm=42.0,
                                       origen='IMPORTED', ordre=1)

    def test_bases_iguals_copia_valors_com_a_COPIED(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        resp = self._copiar(dst, self.src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['seeded'], 2)
        self.assertEqual(resp.data['values_copied'], 2)
        self.assertEqual(resp.data['skipped'], 0)
        self.assertFalse(resp.data['valors_bloquejats_per_talla'])

        a = BaseMeasurement.objects.get(model=dst, pom=self.pom_a)
        # L'origen NO viatja verbatim: un MANUAL copiat mentiria sobre qui va mesurar aquí.
        self.assertEqual(a.origen, 'COPIED')
        self.assertEqual(a.base_value_cm, 60.0)
        self.assertEqual(a.nom_fitxa, 'A')
        self.assertEqual(str(a.tolerancia_minus), '0.50')
        self.assertTrue(a.is_key)
        # Les notes són afirmacions SOBRE l'altre model: no viatgen.
        self.assertIn(a.notes, (None, ''))
        self.assertEqual(BaseMeasurement.objects.get(model=dst, pom=self.pom_b).origen, 'COPIED')

    def test_bases_divergents_nomes_pertinenca_i_avis(self):
        dst = self._model(size_system=self.ss, base_size_label='L')
        resp = self._copiar(dst, self.src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['valors_bloquejats_per_talla'])
        self.assertEqual(resp.data['seeded'], 2)
        self.assertEqual(resp.data['values_copied'], 0)
        self.assertTrue(any('TALLES DIVERGENTS' in w for w in resp.data['warnings']))
        for pom in (self.pom_a, self.pom_b):
            fila = BaseMeasurement.objects.get(model=dst, pom=pom)
            self.assertEqual(fila.origen, 'TEMPLATE')
            self.assertIsNone(fila.base_value_cm)

    def test_run_copiat_fa_coincidir_les_bases(self):
        """Amb `copy_run`, un destí sense talla base rep la de l'origen i els valors passen."""
        dst = self._model()
        resp = self._copiar(dst, self.src, {'copy_files': False})
        self.assertTrue(resp.data['run_copied'])
        self.assertEqual(resp.data['values_copied'], 2)
        dst.refresh_from_db()
        self.assertEqual(dst.base_size_label, 'M')
        self.assertEqual(dst.size_run_model, 'S·M·L')
        self.assertEqual(dst.size_system_id, self.ss.id)

    def test_desti_amb_mesures_ignora_el_run_amb_avis(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        BaseMeasurement.objects.create(model=dst, pom=self.pom_a, base_value_cm=99.0,
                                       origen='MANUAL', ordre=0)
        resp = self._copiar(dst, self.src, {'copy_files': False})
        self.assertFalse(resp.data['run_copied'])
        self.assertTrue(any('IGNORAT' in w for w in resp.data['warnings']))

    def test_sobirania_no_trepitja_manual(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        BaseMeasurement.objects.create(model=dst, pom=self.pom_a, base_value_cm=99.0,
                                       origen='MANUAL', ordre=0)
        resp = self._copiar(dst, self.src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.data['skipped'], 1)
        self.assertEqual(resp.data['seeded'], 1)      # només el POM que faltava
        self.assertEqual(resp.data['values_copied'], 1)
        intacta = BaseMeasurement.objects.get(model=dst, pom=self.pom_a)
        self.assertEqual(intacta.base_value_cm, 99.0)
        self.assertEqual(intacta.origen, 'MANUAL')

    def test_omple_template_buit(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        BaseMeasurement.objects.create(model=dst, pom=self.pom_a, base_value_cm=None,
                                       origen='TEMPLATE', ordre=0)
        resp = self._copiar(dst, self.src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.data['values_copied'], 2)
        fila = BaseMeasurement.objects.get(model=dst, pom=self.pom_a)
        self.assertEqual(fila.origen, 'COPIED')
        self.assertEqual(fila.base_value_cm, 60.0)

    def test_subconjunt_pom_ids(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        resp = self._copiar(dst, self.src, {'pom_ids': [self.pom_b.id],
                                            'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.data['seeded'], 1)
        self.assertEqual(BaseMeasurement.objects.filter(model=dst).count(), 1)
        self.assertTrue(BaseMeasurement.objects.filter(model=dst, pom=self.pom_b).exists())

    def test_mateix_model_400(self):
        resp = self._copiar(self.src, self.src)
        self.assertEqual(resp.status_code, 400)

    def test_origen_buit_400(self):
        buit = self._model()
        dst = self._model()
        resp = self._copiar(dst, buit)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'origen_buit')

    def test_copy_values_false_deixa_la_pertinenca_sense_valor(self):
        dst = self._model(size_system=self.ss, base_size_label='M')
        resp = self._copiar(dst, self.src, {'copy_values': False, 'copy_run': False,
                                            'copy_files': False})
        self.assertEqual(resp.data['seeded'], 2)
        self.assertEqual(resp.data['values_copied'], 0)
        self.assertEqual(
            BaseMeasurement.objects.filter(model=dst, origen='TEMPLATE').count(), 2)


class CopiaGradingTest(_BaseCopiaTest):
    """La graduació: assignar la FK i re-materialitzar, com fa `update_model_step2`."""

    PREFIX = 'CPYG'

    def test_copia_ruleset_i_materialitza_regles(self):
        ss = self._size_system()
        pom = self._pom('A')
        rs = GradingRuleSet.objects.create(nom=self._codi('RS'), size_system=ss)
        GradingRule.objects.create(rule_set=rs, pom=pom, logica='LINEAR', increment=1.0,
                                   talla_base=SizeDefinition.objects.get(
                                       size_system=ss, etiqueta='M'))
        src = self._model(size_system=ss, base_size_label='M', grading_rule_set=rs)
        BaseMeasurement.objects.create(model=src, pom=pom, base_value_cm=60.0, origen='MANUAL')
        dst = self._model(size_system=ss, base_size_label='M')

        resp = self._copiar(dst, src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['grading_set'], rs.id)
        self.assertEqual(resp.data['regles_materialitzades'], 1)
        dst.refresh_from_db()
        self.assertEqual(dst.grading_rule_set_id, rs.id)
        self.assertEqual(ModelGradingRule.objects.filter(model=dst).count(), 1)

    def test_ruleset_buit_avisa_en_comptes_de_callar(self):
        ss = self._size_system()
        pom = self._pom('A')
        rs = GradingRuleSet.objects.create(nom=self._codi('RSBUIT'), size_system=ss)
        src = self._model(size_system=ss, base_size_label='M', grading_rule_set=rs)
        BaseMeasurement.objects.create(model=src, pom=pom, base_value_cm=60.0, origen='MANUAL')
        dst = self._model(size_system=ss, base_size_label='M')

        resp = self._copiar(dst, src, {'copy_run': False, 'copy_files': False})
        self.assertEqual(resp.data['regles_materialitzades'], 0)
        self.assertTrue(any('SENSE regles residents' in w for w in resp.data['warnings']))


class CopiaFitxersTest(_BaseCopiaTest):
    """Els fitxers copiats neixen amb la versió i el nom del DESTÍ, i porten procedència."""

    PREFIX = 'CPYF'

    def test_fitxers_copiats_amb_versio_propia(self):
        from fhort.models_app.services_fitxers import save_model_file

        src = self._model(base_size_label='M')
        dst = self._model(base_size_label='M')
        save_model_file(src, ContentFile(b'<svg/>', name='qualsevol.svg'),
                        tipus='SKETCH_SVG', nom='ORIGEN_SKETCH_SVG_007.svg')
        # El destí ja té una versió pròpia d'aquest tipus: la còpia hi encadena (NNN=2).
        save_model_file(dst, ContentFile(b'<svg/>', name='previ.svg'),
                        tipus='SKETCH_SVG', nom='PREVI.svg')
        # DOCUMENT no viatja mai.
        save_model_file(src, ContentFile(b'%PDF-', name='doc.pdf'),
                        tipus='DOCUMENT', nom='ORIGEN_DOCUMENT_001.pdf')

        resp = self._copiar(dst, src, {'copy_run': False})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['files_copied'], 1)

        self.assertFalse(ModelFitxer.objects.filter(model=dst, tipus='DOCUMENT').exists())
        nou = ModelFitxer.objects.get(model=dst, tipus='SKETCH_SVG', is_current=True)
        self.assertEqual(nou.versio, 2)
        self.assertEqual(nou.nom_fitxer, f'{dst.codi_intern}_SKETCH_SVG_002.svg')
        self.assertEqual(nou.derivat_de_model.model_id, src.id)
        # La cadena del destí queda coherent: el previ deixa de ser el cap.
        self.assertEqual(ModelFitxer.objects.filter(
            model=dst, tipus='SKETCH_SVG', is_current=True).count(), 1)
