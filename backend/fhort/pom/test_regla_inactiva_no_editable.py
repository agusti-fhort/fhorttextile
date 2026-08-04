"""3.5 — L'API DEIXA DE DIR OK A UNA ESCRIPTURA SENSE EFECTE.

`GradingRuleViewSet.destroy` no esborra: marca `actiu=False`. El motor NOMÉS llegeix regles
actives (`_load_grading_rules`, pom/services.py), i el viewset NO filtra per `actiu` —a
posta: cal poder consultar les inactives i reactivar-les—, de manera que una regla
«esborrada» seguia sent editable i responia 200. El tècnic tocava una regla que el motor no
llegiria mai, i el sistema li deia que sí.

El que aquests tests fixen NO és què llegeix el motor (`actiu=True` és correcte i és zona de
motor, no es toca) ni que les inactives ressuscitin soles: és que l'API digui el que passa.

Convenció del repo: `python manage.py test fhort.pom` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import (
    GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
)


class ReglaInactivaNoEsEditableTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='configurador')
        # CONFIGURE és el permís d'escriptura d'aquest viewset; el signal crea el perfil
        # amb el rol per defecte (technician), que NO en té. S'assigna explícitament i es
        # rellegeix l'usuari perquè `force_authenticate` no passi el rol vell cachejat.
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Configurador'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        ss = SizeSystem.objects.create(codi='SS_RI', nom='SS regla inactiva',
                                       base_unit='ALPHA')
        self.talla_base = SizeDefinition.objects.create(size_system=ss, etiqueta='M', ordre=2)
        self.rs = GradingRuleSet.objects.create(nom='RS regla inactiva')
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.regla = GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.talla_base,
            logica='LINEAR', increment_base=2,
        )

        self.client_api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.client_api.force_authenticate(user=self.user)
        self.url = f'/api/v1/grading-rules/{self.regla.pk}/'

    def _desactiva(self):
        """La porta real: DELETE fa soft-delete (no esborra la fila)."""
        resp = self.client_api.delete(self.url)
        self.assertEqual(resp.status_code, 200)
        self.regla.refresh_from_db()
        self.assertFalse(self.regla.actiu, 'DELETE ha de deixar la regla inactiva')

    # ── el defecte ───────────────────────────────────────────────────────────
    def test_editar_una_regla_INACTIVA_ja_no_respon_200(self):
        """Amb el codi vell això peta: responia 200 i desava un canvi que el motor
        no llegiria mai."""
        self._desactiva()

        resp = self.client_api.patch(self.url, {'increment_base': 9}, format='json')

        self.assertEqual(resp.status_code, 409, f'esperava 409, ha fet {resp.status_code}')
        self.assertEqual(resp.data['error'], 'regla_inactiva')

    def test_i_el_valor_NO_s_ha_desat(self):
        """Un 409 no pot deixar el canvi escrit: negar i desar alhora seria pitjor que mentir."""
        self._desactiva()

        self.client_api.patch(self.url, {'increment_base': 9}, format='json')

        self.regla.refresh_from_db()
        self.assertEqual(float(self.regla.increment_base), 2.0)

    def test_el_409_DIU_la_sortida(self):
        """El guard no només nega: diu com desbloquejar-ho (mateix idioma que el 409 del
        segell de grading)."""
        self._desactiva()

        resp = self.client_api.patch(self.url, {'increment_base': 9}, format='json')

        self.assertEqual(resp.data['sortida']['accio'], 'reactivar')
        self.assertTrue(resp.data['sortida']['body']['actiu'])

    # ── el que NO s'ha de trencar ────────────────────────────────────────────
    def test_una_regla_ACTIVA_segueix_essent_editable(self):
        """El guard és per a les inactives; el camí normal no es toca."""
        resp = self.client_api.patch(self.url, {'increment_base': 5}, format='json')

        self.assertEqual(resp.status_code, 200)
        self.regla.refresh_from_db()
        self.assertEqual(float(self.regla.increment_base), 5.0)

    def test_REACTIVAR_una_regla_inactiva_SI_que_passa(self):
        """L'única escriptura sobre una inactiva que SÍ té efecte sobre el motor. Sense
        això el guard deixaria les regles inactives mortes per sempre."""
        self._desactiva()

        resp = self.client_api.patch(self.url, {'actiu': True}, format='json')

        self.assertEqual(resp.status_code, 200)
        self.regla.refresh_from_db()
        self.assertTrue(self.regla.actiu)

    def test_llegir_una_regla_inactiva_segueix_viu(self):
        """El guard és d'ESCRIPTURA. La consulta no es toca: cal poder-les veure per
        decidir si es reactiven."""
        self._desactiva()

        resp = self.client_api.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['actiu'])
