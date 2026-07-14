"""
Management command: provision_free_tenant
F3 P-FREE-SEED (B3) — orquestra la sembra automàtica d'un tenant Free.

    manage.py provision_free_tenant <schema> [--profile <id>] [--email <email>]

QUÈ FA, en ordre:
  1. bootstrap_tenant <schema> --profile <default_free>  (sembra el catàleg del perfil;
     en acabar verd, JA tanca onboarding → actiu, DC-6).
  2. create_tenant_admin <schema> --email <email_facturacio>  (el primer admin, perquè
     el Free sigui autònom).
Cada pas escriu al Registre d'activitat (backoffice.BackofficeActionLog). Èxit → tenant
actiu amb admin. Fallada d'un pas → es registra l'error i la comanda és RE-EXECUTABLE
(bootstrap i create_tenant_admin són idempotents).

DESACOBLAMENT: `ClientViewSet.create` la llança en un subprocés detached (start_new_session)
i torna 201 immediatament; el frontend fa polling de `Client.estat` (onboarding→actiu). Aquí
NO se sap res d'HTTP: només ORM + call_command + log.

DECISIONS: perfil = el SeedProfile marcat is_default_free (o --profile explícit). Email de
l'admin = `Client.email_facturacio` de la fitxa (decisió A5); si és buit, l'admin queda
DIFERIT (log clar) i no s'inventa cap email — re-executable quan s'informi.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model

from fhort.backoffice.models import BackofficeActionLog, SeedProfile


def _log(schema, accio, ok, detall):
    BackofficeActionLog.objects.create(
        usuari=None,  # sembra automàtica del sistema, no d'un usuari de backoffice
        accio=accio,
        objecte_tipus='Client',
        objecte_id=schema,
        detall={'ok': ok, **detall},
    )


class Command(BaseCommand):
    help = "Sembra automàtica d'un tenant Free: bootstrap (perfil) + admin. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument('schema', type=str)
        parser.add_argument('--profile', dest='profile', type=int, default=None,
                            help='ID del SeedProfile. Per defecte, el is_default_free.')
        parser.add_argument('--email', dest='email', type=str, default=None,
                            help="Email de l'admin. Per defecte, Client.email_facturacio.")

    def handle(self, *args, **options):
        schema = options['schema']
        client = get_tenant_model().objects.filter(schema_name=schema).first()
        if client is None:
            raise CommandError(f"Tenant '{schema}' no existeix.")

        # Perfil de sembra: explícit o el default-Free.
        if options['profile'] is not None:
            profile = SeedProfile.objects.filter(pk=options['profile']).first()
        else:
            profile = SeedProfile.objects.filter(is_default_free=True, actiu=True).first()
        if profile is None:
            _log(schema, 'client.seed.bootstrap', False,
                 {'error': 'cap SeedProfile default-Free actiu (ni --profile)'})
            raise CommandError('Cap SeedProfile per sembrar (marca un is_default_free actiu).')

        # 1) Bootstrap del catàleg segons el perfil.
        try:
            call_command('bootstrap_tenant', schema, '--profile', str(profile.pk))
            _log(schema, 'client.seed.bootstrap', True,
                 {'profile': profile.nom, 'profile_id': profile.pk})
        except Exception as e:
            _log(schema, 'client.seed.bootstrap', False,
                 {'profile': profile.nom, 'error': str(e)})
            raise CommandError(f'bootstrap del perfil fallit: {e}')

        # 2) Admin del tenant (email de la fitxa). Si no n'hi ha, es difereix (no s'inventa).
        email = (options['email'] or client.email_facturacio or '').strip()
        if not email:
            _log(schema, 'client.seed.admin', False,
                 {'error': 'sense email_facturacio a la fitxa: admin DIFERIT, re-executable'})
            self.stdout.write(self.style.WARNING(
                f"Tenant '{schema}' sembrat, però admin DIFERIT (falta email_facturacio). "
                f"Informa'l i re-executa."))
            return

        try:
            call_command('create_tenant_admin', schema, '--email', email)
            _log(schema, 'client.seed.admin', True, {'email': email})
        except Exception as e:
            _log(schema, 'client.seed.admin', False, {'email': email, 'error': str(e)})
            raise CommandError(f'creació admin fallida: {e}')

        self.stdout.write(self.style.SUCCESS(
            f"Tenant Free '{schema}' provisionat: catàleg ({profile.nom}) + admin ({email})."))
