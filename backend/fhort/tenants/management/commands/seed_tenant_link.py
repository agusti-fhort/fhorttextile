"""
Management command: seed_tenant_link
Federació v2 (P1) — sembra el primer vincle de federació: Brand=LOS ↔ Studio=FTT.

    manage.py seed_tenant_link [--brand LOS] [--studio FTT]

Idempotent: si el vincle (brand, studio) ja existeix, el MOSTRA (amb el seu token) i
no en crea cap altre ni en regenera el token. El vincle viu a `public` (tenants és
SHARED) i no cal cap `schema_context`. La validació de tipologies (marca↔estudi) la fa
`TenantLink.clean()` abans de desar; si falla, la comanda avorta amb l'error clar.
"""
from django.core.management.base import BaseCommand, CommandError

from fhort.tenants.models import TenantLink


class Command(BaseCommand):
    help = 'Sembra (o mostra) el vincle de federació Brand↔Studio. Idempotent.'

    def add_arguments(self, parser):
        parser.add_argument('--brand', default='LOS', help='codi_tenant del Brand (marca).')
        parser.add_argument('--studio', default='FTT', help='codi_tenant de l\'Studio (estudi).')

    def handle(self, *args, **options):
        brand, studio = options['brand'], options['studio']

        link = TenantLink.objects.filter(
            brand_codi_tenant=brand, studio_codi_tenant=studio,
        ).first()
        if link is not None:
            self.stdout.write(self.style.WARNING(
                f'El vincle {brand} ↔ {studio} ja existeix (estat={link.estat}).'))
            self.stdout.write(f'  token: {link.token}')
            return

        link = TenantLink(
            brand_codi_tenant=brand, studio_codi_tenant=studio,
            token=TenantLink.genera_token(),   # abans del full_clean: token és obligatori
        )
        try:
            link.full_clean()   # valida tipologies (marca↔estudi) + la resta de camps
        except Exception as e:
            raise CommandError(f'Vincle no vàlid: {e}')
        link.save()

        self.stdout.write(self.style.SUCCESS(
            f'Vincle de federació creat: {brand} (marca) ↔ {studio} (estudi), estat={link.estat}.'))
        self.stdout.write(f'  token: {link.token}')
