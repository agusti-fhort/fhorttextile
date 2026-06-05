# Sprint 1 — Capa 9: alta/actualització d'un administrador del backoffice.
import getpass
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name

from fhort.backoffice.models import BackofficeUser


def _read_password():
    """Obté la contrasenya sense exposar-la a argv ni a l'historial.

    En un terminal interactiu la demana dues vegades amb getpass i confirma.
    Quan l'entrada està redirigida (pipe) en llegeix una sola línia.
    """
    if sys.stdin.isatty():
        password = getpass.getpass('Password: ')
        if password != getpass.getpass('Confirma password: '):
            raise CommandError('Les contrasenyes no coincideixen.')
    else:
        password = sys.stdin.readline().rstrip('\n')
    if not password:
        raise CommandError('La contrasenya no pot ser buida.')
    return password


class Command(BaseCommand):
    help = (
        'Crea (o actualitza) un auth.User + BackofficeUser amb rol ADMIN al '
        'schema public. El backoffice mai entra als schemas dels tenants.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument(
            '--password',
            default=None,
            help='Opcional; si s\'omet es demana de forma interactiva (getpass).',
        )
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')

    @transaction.atomic
    def handle(self, *args, **options):
        # Guarda no negociable: l'usuari de backoffice viu només al public.
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "Aquest command només es pot executar al schema public "
                f"(actual: '{connection.schema_name}'). Els usuaris de "
                'backoffice mai viuen en un tenant.'
            )

        email = options['email'].strip().lower()
        password = options['password'] or _read_password()
        first_name = options['first_name']
        last_name = options['last_name']

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.set_password(password)
        user.save()

        perfil, _ = BackofficeUser.objects.update_or_create(
            usuari=user,
            defaults={'rol': BackofficeUser.Rol.ADMIN, 'actiu': True},
        )

        accio = 'creat' if created else 'actualitzat'
        self.stdout.write(
            self.style.SUCCESS(
                f'Usuari backoffice {accio}: {email} · rol={perfil.rol} · '
                f'actiu={perfil.actiu}'
            )
        )
