"""Tests del camí PDF/imatge del "Nou run de client" (Size Library, pas 2).

Regressió del bug del contracte d'esquema (DIAGNOSI_IMPORT_RUN_CLIENT_2026-07-07): el
consumidor llegia `measurements` (esquema del wizard) però el servei G3 retorna `poms` +
`grading_table`. Aquí es verifica la normalització alineada i que l'avís de zero POMs es manté.
"""
import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.size_map_views import _pdf_extracted_to_poms, size_map_grading_preview_file_view


class PdfExtractedToPomsTest(TestCase):
    """Helper pur: esquema `poms` + `grading_table` → [{codi_fitxa, descripcio, values}]."""

    def test_amb_grading_table(self):
        extracted = {
            'poms': [{'code': 'B', 'description': 'CHEST WIDTH', 'base_value_cm': 22.5}],
            'grading_table': [{'code': 'B', 'values_by_size': {'S': 21.5, 'M': 22.5, 'L': 23.5}}],
            'base_size': {'value': 'M'},
        }
        out = _pdf_extracted_to_poms(extracted, 'M')
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['codi_fitxa'], 'B')
        self.assertEqual(out[0]['descripcio'], 'CHEST WIDTH')
        self.assertEqual(out[0]['values'], {'S': 21.5, 'M': 22.5, 'L': 23.5})

    def test_base_only_sense_grading_usa_base_del_document(self):
        extracted = {
            'poms': [{'code': 'C', 'description': 'WAIST', 'base_value_cm': 30.0}],
            'grading_table': [],
            'has_base_only': True,
            'base_size': {'value': 'M'},
        }
        out = _pdf_extracted_to_poms(extracted, '')   # base_size buit → talla base del document
        self.assertEqual(out[0]['values'], {'M': 30.0})

    def test_base_size_del_formdata_preval(self):
        extracted = {'poms': [{'code': 'C', 'base_value_cm': 30.0}], 'grading_table': [],
                     'base_size': {'value': 'M'}}
        out = _pdf_extracted_to_poms(extracted, 'L')   # el FormData mana sobre el detectat
        self.assertEqual(out[0]['values'], {'L': 30.0})

    def test_zero_poms(self):
        self.assertEqual(_pdf_extracted_to_poms({'poms': [], 'grading_table': []}, 'M'), [])
        self.assertEqual(_pdf_extracted_to_poms({}, 'M'), [])


class SizeMapPreviewFileViewTest(TenantTestCase):
    """Vista: amb esquema `poms` vàlid NO salta l'avís de "cap mesura"; buit → avís es manté."""

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
        self.user = get_user_model().objects.create(username='cfg')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.rol_nom = 'admin'
        self.profile.permisos = {'grant': ['configure']}
        self.profile.save()
        self.user = get_user_model().objects.get(pk=self.user.pk)   # neteja cache O2O

    def _post_pdf(self):
        req = APIRequestFactory().post(
            '/api/v1/size-map/grading-preview-file/',
            {'file': SimpleUploadedFile('BERG.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
             'base_size': 'M'}, format='multipart')
        force_authenticate(req, user=self.user)
        return req

    @patch('fhort.models_app.extraction_service.extract_from_file')
    def test_poms_valids_no_disparen_avis_cap_mesura(self, mock_extract):
        mock_extract.return_value = {
            'poms': [{'code': 'B', 'description': 'CHEST WIDTH', 'base_value_cm': 22.5}],
            'grading_table': [{'code': 'B', 'values_by_size': {'S': 21.5, 'M': 22.5}}],
            'base_size': {'value': 'M'},
        }
        resp = size_map_grading_preview_file_view(self._post_pdf())
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("La IA no ha retornat cap mesura llegible del document.",
                         resp.data.get('avisos', []))
        self.assertIn('S', resp.data.get('run', []))   # talles derivades de la graduació

    @patch('fhort.models_app.extraction_service.extract_from_file')
    def test_zero_poms_mante_avis(self, mock_extract):
        mock_extract.return_value = {'poms': [], 'grading_table': []}
        resp = size_map_grading_preview_file_view(self._post_pdf())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("La IA no ha retornat cap mesura llegible del document.",
                      resp.data.get('avisos', []))


class _FakeResp:
    def __init__(self, data): self._data = data
    def raise_for_status(self): pass
    def json(self): return self._data


class _FakeClient:
    def __init__(self, data): self._data = data
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def post(self, *a, **k): return _FakeResp(self._data)


class ExtractFromFileTruncationTest(TestCase):
    """Guarda de truncament (R4) al servei G3: stop_reason='max_tokens' → anomalia no bloquejant."""

    @patch('fhort.models_app.extraction_service._get_api_key', return_value='k')
    @patch('fhort.models_app.extraction_service.httpx.Client')
    def test_max_tokens_afegeix_anomalia(self, mock_client, _mk):
        from fhort.models_app import extraction_service as svc
        mock_client.return_value = _FakeClient(
            {'stop_reason': 'max_tokens', 'content': [{'text': '{"poms": [], "grading_table": []}'}]})
        result = svc.extract_from_file(b'%PDF-1.4', 'x.pdf')
        self.assertTrue(any('truncada' in a for a in result.get('anomalies_detected', [])))

    @patch('fhort.models_app.extraction_service._get_api_key', return_value='k')
    @patch('fhort.models_app.extraction_service.httpx.Client')
    def test_end_turn_no_afegeix_anomalia(self, mock_client, _mk):
        from fhort.models_app import extraction_service as svc
        mock_client.return_value = _FakeClient(
            {'stop_reason': 'end_turn', 'content': [{'text': '{"poms": [], "grading_table": []}'}]})
        result = svc.extract_from_file(b'%PDF-1.4', 'x.pdf')
        self.assertNotIn('truncada', ' '.join(result.get('anomalies_detected', [])))
