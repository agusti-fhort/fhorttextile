"""Tests de l'import massiu de models (col·lecció Excel) — models_app.

Convenció del repo: mòdul de tests pla dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

El que aquests tests defensen és una sola frase: **el comptador del bulk no pot
contradir els models que ja hi ha a la BD.** Tres camins escriuen `sequencial`
(signal MAX, wizard MAX, bulk ModelSequence) i només l'últim mira el comptador;
si el comptador es mira només a si mateix, el primer import d'un client que ja té
models reserva l'1 i xoca contra codi_intern (unique) → IntegrityError → 500.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (
    BulkCollectionImport, BulkCollectionRow, Model, ModelSequence)
from fhort.models_app.bulk_import_service import commit_import
from fhort.models_app.services import reserve_sequence_range
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant


class _BulkBase(_TenantBase):
    """Client BRW + perfil tècnic + helpers per muntar una importació previsada."""

    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie SL')
        user = get_user_model().objects.create_user(username='tec', password='x')
        # El perfil el pot haver creat ja un signal d'accounts en néixer l'usuari.
        self.profile, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})

    def _manual_models(self, n, year=2026, season='FW'):
        """Models creats pel camí del wizard: codi_intern + sequencial explícits (el signal
        no hi toca). Cap d'ells actualitza ModelSequence — aquest és el terreny real."""
        yy = str(year)[-2:]
        for i in range(1, n + 1):
            Model.objects.create(
                codi_intern=f"BRW-{season}{yy}-{str(i).zfill(4)}",
                customer=self.customer, codi_tenant='BRW',
                any=year, temporada=season, sequencial=i,
                nom_prenda=f"Manual {i}", estat='Nou',
            )

    def _previsat(self, noms, year=2026, season='FW'):
        """Una importació PREVISADA amb una fila OK per nom (mínim viable: nom/any/temporada)."""
        imp = BulkCollectionImport.objects.create(
            customer=self.customer, creat_per=self.profile, estat='PREVISAT', resum={}, resultat=[])
        BulkCollectionRow.objects.bulk_create([
            BulkCollectionRow(
                importacio=imp, row_num=i, estat='OK', errors=[],
                raw_data={'nom_prenda': nom, 'any': str(year), 'temporada': season},
            )
            for i, nom in enumerate(noms, start=2)
        ])
        return imp


class ComptadorMonotonTest(_BulkBase):
    """T1 — reserve_sequence_range no pot tornar un número que ja és al terreny."""

    def test_comptador_buit_amb_models_manuals_continua_del_max_real(self):
        # El cas EXACTE de Brownie a PROD: 15 models manuals, comptador inexistent.
        self._manual_models(15)
        self.assertFalse(ModelSequence.objects.filter(customer=self.customer).exists())

        first, last = reserve_sequence_range(self.customer, 2026, 'FW', 5)

        self.assertEqual((first, last), (16, 20))

    def test_comptador_no_retrocedeix_si_va_per_davant_del_terreny(self):
        # Comptador avançat (imports previs) + pocs models al terreny → mana el comptador.
        self._manual_models(3)
        ModelSequence.objects.create(customer=self.customer, year=2026, season='FW', last_seq=40)

        first, last = reserve_sequence_range(self.customer, 2026, 'FW', 2)

        self.assertEqual((first, last), (41, 42))

    def test_reserva_escopada_per_temporada_i_any(self):
        # El MAX real d'una (any, temporada) no contamina les altres claus.
        self._manual_models(15, year=2026, season='FW')

        self.assertEqual(reserve_sequence_range(self.customer, 2026, 'SS', 2), (1, 2))
        self.assertEqual(reserve_sequence_range(self.customer, 2027, 'FW', 2), (1, 2))


class ImportSenseColisioTest(_BulkBase):
    """T1 — el cas de PROD punta a punta: import massiu sobre un client que ja té models."""

    def test_import_massiu_sobre_models_manuals_no_colisiona(self):
        self._manual_models(15)   # BRW-FW26-0001 .. BRW-FW26-0015
        imp = self._previsat(['Tate', 'Rosalia', 'Mika', 'Noa', 'Vera'])

        stats = commit_import(imp, self.profile)

        self.assertEqual(stats['models'], 5)
        nous = list(Model.objects.filter(customer=self.customer, any=2026, temporada='FW')
                    .order_by('sequencial').values_list('codi_intern', flat=True))
        self.assertEqual(nous[15:], [
            'BRW-FW26-0016', 'BRW-FW26-0017', 'BRW-FW26-0018',
            'BRW-FW26-0019', 'BRW-FW26-0020',
        ])
        # 20 codis, tots diferents: cap col·lisió amb el terreny previ.
        self.assertEqual(len(nous), 20)
        self.assertEqual(len(set(nous)), 20)

    def test_dos_imports_seguits_continuen_la_serie(self):
        self._manual_models(15)
        commit_import(self._previsat(['A', 'B']), self.profile)
        commit_import(self._previsat(['C', 'D']), self.profile)

        codis = set(Model.objects.filter(customer=self.customer).values_list('codi_intern', flat=True))
        self.assertIn('BRW-FW26-0018', codis)
        self.assertIn('BRW-FW26-0019', codis)
        self.assertEqual(len(codis), 19)
