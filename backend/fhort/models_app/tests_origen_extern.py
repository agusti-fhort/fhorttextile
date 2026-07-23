"""Model.origen EXTERN — la provinença de federació no enverina la seqüència local.

Convenció del repo: mòdul de tests pla dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

El que defensen (Federació v2, P2 · Bandera 1 de la diagnosi):
  · Un model EXTERN conserva el sequencial del Brand però NO compta per al terra local:
    reserve_sequence_range mai salta a l'espai de numeració de l'altra casa.
  · L'escapatòria del signal segueix intacta: un codi_intern imposat no es regenera.
  · El default és INTERN — cap camí existent (wizard/bulk) canvia de comportament.
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model, ModelSequence
from fhort.models_app.services import _real_max_seq, reserve_sequence_range, sequence_floor
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant


class OrigenExternTest(_TenantBase):

    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie SL')

    def _model(self, codi, seq, origen=Model.ORIGEN_INTERN, year=2027, season='SS'):
        return Model.objects.create(
            codi_intern=codi, customer=self.customer, codi_tenant='BRW',
            any=year, temporada=season, sequencial=seq, origen=origen,
            nom_prenda=codi,
        )

    # ── escapatòria del signal ─────────────────────────────────────────────────
    def test_codi_imposat_extern_no_es_regenera_ni_consumeix_comptador(self):
        """codi_intern imposat → el signal retorna d'hora: ni el toca ni crea ModelSequence."""
        m = self._model('LOS-SS27-4711', 4711, origen=Model.ORIGEN_EXTERN)
        m.refresh_from_db()
        self.assertEqual(m.codi_intern, 'LOS-SS27-4711')
        self.assertEqual(m.sequencial, 4711)
        self.assertEqual(m.origen, Model.ORIGEN_EXTERN)
        self.assertFalse(ModelSequence.objects.filter(customer=self.customer).exists())

    # ── el terra ignora els EXTERN ─────────────────────────────────────────────
    def test_real_max_seq_ignora_extern(self):
        self._model('BRW-SS27-0015', 15, origen=Model.ORIGEN_INTERN)
        self._model('LOS-SS27-4711', 4711, origen=Model.ORIGEN_EXTERN)
        # El terra local és 15 (l'INTERN), no 4711.
        self.assertEqual(_real_max_seq(self.customer, 2027, 'SS'), 15)
        self.assertEqual(sequence_floor(self.customer, 2027, 'SS'), 15)

    def test_reserve_no_salta_a_l_espai_del_brand(self):
        self._model('BRW-SS27-0015', 15, origen=Model.ORIGEN_INTERN)
        self._model('LOS-SS27-4711', 4711, origen=Model.ORIGEN_EXTERN)
        first, last = reserve_sequence_range(self.customer, 2027, 'SS', 3)
        # Continua del 15 real, NO del 4711 extern.
        self.assertEqual((first, last), (16, 18))

    def test_nomes_extern_no_ocupa_terreny(self):
        """Un client amb NOMÉS models externs comença la seva numeració pròpia per 1."""
        self._model('LOS-SS27-4711', 4711, origen=Model.ORIGEN_EXTERN)
        self.assertEqual(_real_max_seq(self.customer, 2027, 'SS'), 0)
        self.assertEqual(reserve_sequence_range(self.customer, 2027, 'SS', 2), (1, 2))

    # ── default INTERN ─────────────────────────────────────────────────────────
    def test_default_intern(self):
        """Sense especificar origen (camí wizard/bulk), el model neix INTERN i compta."""
        m = self._model('BRW-SS27-0001', 1)   # sense origen= → default
        self.assertEqual(m.origen, Model.ORIGEN_INTERN)
        self.assertEqual(_real_max_seq(self.customer, 2027, 'SS'), 1)
