"""ModelConsumptionEvent.actor_schema — l'ACTOR de la meritació (Federació v2, P4).

Les lleis que defensen:
  · L'EVENT PORTA QUI MERITA. El receiver escriu actor_schema del signal a public.
  · SIGNAL NU = COMPATIBLE. Un emissor que no passa actor no trenca res (default '').
  · GET_OR_CREATE NO REESCRIU. Un opaque_ref ja existent conserva el seu actor.
  · BACKFILL: els events històrics queden a 'fhort' (veritat verificada).
  · RECONCILE passa el schema del tenant que recorre.

    cd backend && venv/bin/python manage.py test fhort.backoffice.tests_actor_schema
"""
import importlib
import uuid

from django.apps import apps as global_apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from fhort.accounts.models import UserProfile
from fhort.backoffice.models import ModelConsumptionEvent
from fhort.tasks.signals import model_consumption_started

User = get_user_model()


class ActorSchemaTest(TenantTestCase):

    def setUp(self):
        with schema_context('public'):
            ModelConsumptionEvent.objects.all().delete()

    def _send(self, opaque_ref, actor_schema=None):
        kwargs = dict(
            sender=None, codi_client='BRW', period='2026-06',
            opaque_ref=opaque_ref, merited_at=timezone.now(),
        )
        if actor_schema is not None:
            kwargs['actor_schema'] = actor_schema
        model_consumption_started.send(**kwargs)

    def _event(self, opaque_ref):
        with schema_context('public'):
            return ModelConsumptionEvent.objects.get(opaque_ref=opaque_ref)

    # ── el receiver escriu l'actor ─────────────────────────────────────────────
    def test_nou_event_porta_actor(self):
        ref = uuid.uuid4()
        self._send(ref, actor_schema='fhort')
        self.assertEqual(self._event(ref).actor_schema, 'fhort')

    def test_signal_nu_sense_actor_default_buit(self):
        """Un emissor antic (sense el kwarg) no trenca: l'event neix amb actor ''."""
        ref = uuid.uuid4()
        self._send(ref)   # sense actor_schema
        self.assertEqual(self._event(ref).actor_schema, '')

    def test_get_or_create_no_reescriu_actor(self):
        ref = uuid.uuid4()
        self._send(ref, actor_schema='fhort')
        self._send(ref, actor_schema='altre')   # mateix opaque_ref
        with schema_context('public'):
            self.assertEqual(ModelConsumptionEvent.objects.filter(opaque_ref=ref).count(), 1)
        self.assertEqual(self._event(ref).actor_schema, 'fhort')   # conserva el primer

    # ── backfill de la migració ────────────────────────────────────────────────
    def test_backfill_fixa_fhort(self):
        mig = importlib.import_module(
            'fhort.backoffice.migrations.0011_backfill_actor_schema_fhort')
        with schema_context('public'):
            ref = uuid.uuid4()
            ModelConsumptionEvent.objects.create(
                codi_client='LOS', period='2026-05', opaque_ref=ref,
                merited_at=timezone.now(), actor_schema='')
            mig.backfill_actor_fhort(global_apps, None)
            self.assertEqual(
                ModelConsumptionEvent.objects.get(opaque_ref=ref).actor_schema, 'fhort')

    # ── reconcile passa l'actor del tenant que recorre ─────────────────────────
    def test_reconcile_passa_actor(self):
        from fhort.models_app.models import Model
        from fhort.tasks.models import Customer, ModelTask, TaskTransition, TaskType

        schema = self.tenant.schema_name
        cust = Customer.objects.create(codi='BRW', nom='Brownie SL')
        u, _ = User.objects.get_or_create(username='tec', defaults={'email': 't@x.com'})
        UserProfile.objects.get_or_create(
            user=u, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})
        model = Model.objects.create(
            codi_intern='BRW-FW26-0001', customer=cust, codi_tenant='BRW',
            any=2026, temporada='FW', sequencial=1, nom_prenda='Test',
        )
        tt = TaskType.objects.create(code='patronatge', name='Patronatge')
        task = ModelTask.objects.create(model=model, task_type=tt, status='InProgress')
        TaskTransition.objects.create(model_task=task, to_status='InProgress')

        call_command('reconcile_consumption', tenant=schema, verbosity=0)

        with schema_context('public'):
            ev = ModelConsumptionEvent.objects.filter(codi_client='BRW')
            self.assertEqual(ev.count(), 1)
            self.assertEqual(ev.first().actor_schema, schema)
