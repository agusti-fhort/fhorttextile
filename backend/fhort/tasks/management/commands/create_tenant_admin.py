"""
Management command: create_tenant_admin
P-BOOT / P2 — el primer usuari d'un tenant nou (DC-5 / D6).

    manage.py create_tenant_admin <schema> --email <email> [--password <temp>]

EL CAP-I-CUA QUE RESOL: la porta HTTP de creació d'usuaris (`accounts/views.py`,
`UserViewSet.create`) exigeix estar JA dins el schema del tenant **i** tenir la capacitat
`MANAGE_USERS` — calen usuaris per crear usuaris. Un tenant acabat de provisionar no en té
cap, així que ningú hi pot entrar. Aquesta comanda entra pel costat: obre un
`schema_context(schema)` des de `public` i crea el User allà dins.

MECÀNICA
- Dins `schema_context(schema)`, `connection.schema_name != 'public'` → la guarda del signal
  `accounts/signals.py:24-25` NO salta i el `UserProfile` es crea sol.
- El signal, però, li posa `rol_nom = DEFAULT_ROLE` (= `"technician"`,
  `accounts/capabilities.py:28`), que **no té `MANAGE_USERS`**: el primer usuari no podria
  crear-ne cap més. Per això aquí es força `rol_nom='admin'` DESPRÉS del signal.

DIFERIT AMB NOM: el "forçar canvi de contrasenya al primer login" no s'implementa (exigiria
superfície de frontend al tenant). La contrasenya temporal s'imprimeix UN cop.
"""
import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model, get_public_schema_name

ADMIN_ROLE = 'admin'


def _temp_password(n=16):
    alfabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabet) for _ in range(n))


class Command(BaseCommand):
    help = "Crea el primer usuari administrador d'un tenant (rol_nom='admin')."

    def add_arguments(self, parser):
        parser.add_argument('schema', type=str, help='Schema del tenant.')
        parser.add_argument('--email', type=str, required=True, help="Email = username de l'admin.")
        parser.add_argument('--password', type=str, default=None,
                            help='Contrasenya temporal. Si no es dona, se-n genera una.')

    def handle(self, *args, **options):
        schema, email = options['schema'], options['email'].strip()
        if schema == get_public_schema_name():
            raise CommandError(
                "'public' no és un tenant: per al backoffice usa `create_backoffice_admin`.")
        if not email:
            raise CommandError('--email buit.')

        TenantModel = get_tenant_model()
        if not TenantModel.objects.filter(schema_name=schema).exists():
            raise CommandError(f"Tenant '{schema}' no existeix.")

        generada = options['password'] is None
        password = options['password'] or _temp_password()

        with schema_context(schema):
            from fhort.accounts.models import UserProfile

            # Idempotent: si l'email ja existeix al tenant, no es duplica ni es toca la
            # contrasenya; només s'assegura que el rol sigui admin.
            existent = User.objects.filter(username=email).first()
            if existent is not None:
                prof, _ = UserProfile.objects.get_or_create(
                    user=existent, defaults={'nom_complet': email, 'rol_nom': ADMIN_ROLE,
                                             'permisos': {}})
                if prof.rol_nom != ADMIN_ROLE:
                    prof.rol_nom = ADMIN_ROLE
                    prof.save(update_fields=['rol_nom'])
                    self.stdout.write(self.style.WARNING(
                        f"Usuari '{email}' ja existia a '{schema}': rol elevat a '{ADMIN_ROLE}'."))
                else:
                    self.stdout.write(
                        f"Usuari '{email}' ja existeix a '{schema}' amb rol '{ADMIN_ROLE}'. Res a fer.")
                return

            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, password=password)
                # El signal ja ha creat el UserProfile amb rol 'technician'; el pugem a admin.
                prof = UserProfile.objects.filter(user=user).first()
                if prof is None:
                    raise CommandError(
                        'El signal no ha creat el UserProfile: revisa accounts/signals.py '
                        f'(schema actiu={schema}).')
                prof.rol_nom = ADMIN_ROLE
                prof.nom_complet = prof.nom_complet or email
                prof.save(update_fields=['rol_nom', 'nom_complet'])

        self.stdout.write(self.style.SUCCESS(
            f"\nAdmin creat a '{schema}': {email} (rol={ADMIN_ROLE})"))
        if generada:
            self.stdout.write(self.style.WARNING(
                f"Contrasenya temporal (només es mostra ara): {password}"))
