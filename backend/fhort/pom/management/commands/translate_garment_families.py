"""Traduccions ca/es de les 17 famílies de Garment Types (nom_ca/nom_es).
Idempotent: UPDATE per codi, dins transacció. NOMÉS dades — no toca models.

Decisions (Agus): nom_client es manté = nom_en (la UI /garment-types el mostra; no es toca).
Les traduccions nom_ca/nom_es es veuen al WIZARD (selector i18n-aware). S'apliquen a les DUES
capes: GarmentTypeGlobal (canònic, public + rèplica tenant) i GarmentType del tenant fhort.
Només les 17 famílies ACTIVES (codi); les 42 velles desactivades tenen altres codis → no s'hi toquen.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

TENANT = 'fhort'

# codi → (nom_ca, nom_es)
TRANSLATIONS = {
    'BUTTONED_TOPS':         ('Tops de botonadura',               'Tops abotonados'),
    'JERSEY_TOPS':           ('Tops de punt',                     'Tops de punto'),
    'KNIT_SWEATERS':         ('Jerseis i punts tancats',          'Jerséis y puntos cerrados'),
    'KNIT_CARDIGANS':        ('Càrdigans i punts oberts',         'Cárdigans y puntos abiertos'),
    'SWEATSHIRTS_MIDLAYERS': ('Dessuadores i segones capes',      'Sudaderas y capas medias'),
    'TAILORED_PANTS':        ('Pantalons estructurats',           'Pantalones estructurados'),
    'LEGGINGS_TIGHTS':       ('Malles i leggings',                'Mallas y leggings'),
    'SKIRTS':                ('Faldilles',                        'Faldas'),
    'DRESSES':               ('Vestits',                          'Vestidos'),
    'ADULT_JUMPSUITS':       ("Monos i petos d'adult",            'Monos y petos de adulto'),
    'UNDERWEAR':             ('Roba interior',                    'Ropa interior'),
    'BRA_SHAPEWEAR':         ('Corseteria i suport',              'Corsetería y soporte'),
    'SWIMWEAR':              ('Roba de bany',                     'Ropa de baño'),
    'STRUCTURED_JACKETS':    ('Sastreria i caçadores',            'Sastrería y cazadoras'),
    'HEAVY_OUTERWEAR':       ('Abrics i parques',                 'Abrigos y parkas'),
    'BABY_ONEPIECES':        ('Integrals nadó i infantil',        'Enterizos bebé e infantil'),
    'BABY_SEPARATES':        ('Nadó i infantil — peces separades', 'Bebé e infantil — piezas separadas'),
}


class Command(BaseCommand):
    help = 'Aplica nom_ca/nom_es a les 17 famílies de Garment Types (global + tenant). Idempotent.'

    def handle(self, *args, **options):
        from fhort.pom.models import GarmentTypeGlobal, GarmentType
        rep = {'glob_public': 0, 'glob_tenant': 0, 'gt_tenant': 0, 'no_match': []}

        with transaction.atomic():
            # Capa GLOBAL canònica (public).
            with schema_context('public'):
                for codi, (ca, es) in TRANSLATIONS.items():
                    rep['glob_public'] += GarmentTypeGlobal.objects.filter(codi=codi).update(nom_ca=ca, nom_es=es)
            # Tenant: rèplica global + famílies GarmentType.
            with schema_context(TENANT):
                for codi, (ca, es) in TRANSLATIONS.items():
                    rep['glob_tenant'] += GarmentTypeGlobal.objects.filter(codi=codi).update(nom_ca=ca, nom_es=es)
                    n = GarmentType.objects.filter(codi_client=codi).update(nom_ca=ca, nom_es=es)
                    rep['gt_tenant'] += n
                    if n == 0:
                        rep['no_match'].append(codi)

        line = '─' * 60
        self.stdout.write('\n' + line)
        self.stdout.write('Traduccions Garment Types (nom_ca/nom_es)')
        self.stdout.write(line)
        self.stdout.write('GarmentTypeGlobal PUBLIC actualitzats: %d / 17' % rep['glob_public'])
        self.stdout.write('GarmentTypeGlobal TENANT actualitzats: %d / 17' % rep['glob_tenant'])
        self.stdout.write('GarmentType (tenant) actualitzats: %d / 17' % rep['gt_tenant'])
        self.stdout.write('codis sense match al tenant: %s' % (', '.join(rep['no_match']) or 'cap'))
        self.stdout.write('nom_client: NO tocat (= nom_en, decisió Agus)')
        self.stdout.write(line + '\n')
