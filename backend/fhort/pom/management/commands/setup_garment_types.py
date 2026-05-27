"""
S13-A · Migració GarmentType — Opció B: Global (public) + Tenant reassignat.

Crea 42 GarmentTypeGlobal canònics al schema public, reassigna els 62
GarmentType existents al tenant 'fhort' al global correcte i esborra els
20 duplicats antics.

Adaptació: el model real fa servir `nom_ca` (no `nom_cat`).
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context


# (codi, grup, nom_en, nom_ca, nom_es, display_order)
GARMENT_TYPE_GLOBALS = [
    # TOPS
    ('T_SHIRT',        'TOPS',       'T-shirt',               'Samarreta',              'Camiseta',            1),
    ('SHIRT',          'TOPS',       'Shirt (woven)',         'Camisa',                 'Camisa',              2),
    ('BLOUSE',         'TOPS',       'Blouse',                'Blusa',                  'Blusa',               3),
    ('POLO',           'TOPS',       'Polo shirt',            'Polo',                   'Polo',                4),
    ('TOP_SLEEVELESS', 'TOPS',       'Top (sleeveless)',      'Top sense mànigues',     'Top sin mangas',      5),
    ('BODYSUIT',       'TOPS',       'Bodysuit',              'Body',                   'Body',                6),
    ('SWEATER',        'TOPS',       'Sweater / Jumper',      'Jersei',                 'Jersey',              7),
    ('HOODIE',         'TOPS',       'Hoodie / Sweatshirt',   'Dessuadora',             'Sudadera',            8),
    ('CARDIGAN',       'TOPS',       'Cardigan',              'Cardigan',               'Cárdigan',            9),
    ('VEST_TOP',       'TOPS',       'Vest / Tank top',       'Samarreta de tirants',   'Camiseta tirantes',  10),
    ('BABY_BODYSUIT',  'TOPS',       'Baby bodysuit',         'Body nadó',              'Body bebé',          11),
    ('BABY_TOP',       'TOPS',       'Baby top / T-shirt',    'Samarreta nadó',         'Camiseta bebé',      12),
    # BOTTOMS
    ('TROUSERS',       'BOTTOMS',    'Trousers / Pants',      'Pantalons',              'Pantalones',          1),
    ('JEANS',          'BOTTOMS',    'Jeans (denim)',         'Texans',                 'Vaqueros',            2),
    ('SHORTS',         'BOTTOMS',    'Shorts',                'Pantalons curts',        'Pantalones cortos',   3),
    ('LEGGINGS',       'BOTTOMS',    'Leggings',              'Leggings',               'Leggings',            4),
    ('SKIRT',          'BOTTOMS',    'Skirt',                 'Faldilla',               'Falda',               5),
    ('BABY_LEGGINGS',  'BOTTOMS',    'Baby leggings / pants', 'Pantalons nadó',         'Pantalón bebé',       6),
    # DRESSES
    ('DRESS',          'DRESSES',    'Dress',                 'Vestit',                 'Vestido',             1),
    ('SHIRT_DRESS',    'DRESSES',    'Shirt dress',           'Vestit camiser',         'Vestido camisero',    2),
    ('JUMPSUIT',       'DRESSES',    'Jumpsuit',              'Mono',                   'Mono',                3),
    ('PLAYSUIT',       'DRESSES',    'Playsuit / Romper',     'Mono curt',              'Mono corto',          4),
    ('BABY_ROMPER',    'DRESSES',    'Baby romper / Babygrow','Granota nadó',           'Pelele bebé',         5),
    ('BABY_DRESS',     'DRESSES',    'Baby dress',            'Vestit nadó',            'Vestido bebé',        6),
    # OUTERWEAR
    ('JACKET',         'OUTERWEAR',  'Jacket / Blazer',       'Jaqueta',                'Chaqueta',            1),
    ('COAT',           'OUTERWEAR',  'Coat',                  'Abric',                  'Abrigo',              2),
    ('TRENCH_COAT',    'OUTERWEAR',  'Trench coat',           'Trinxera',               'Gabardina',           3),
    ('PARKA',          'OUTERWEAR',  'Parka / Anorak',        'Parka',                  'Parka',               4),
    ('GILET',          'OUTERWEAR',  'Gilet / Vest',          'Armilla',                'Chaleco',             5),
    ('LEATHER_GARMENT','OUTERWEAR',  'Leather garment',       'Peça de pell',           'Prenda de piel',      6),
    # UNDERWEAR
    ('BRA',            'UNDERWEAR',  'Bra',                   'Sostenidor',             'Sujetador',           1),
    ('BRIEFS_WOMAN',   'UNDERWEAR',  'Briefs (woman)',        'Bragueta dona',          'Braguita',            2),
    ('BOXERS',         'UNDERWEAR',  'Boxers / Briefs (man)', 'Calçotets',              'Calzoncillo',         3),
    ('PYJAMA_SET',     'UNDERWEAR',  'Pyjama set (2-piece)',  'Pijama conjunt',         'Pijama conjunto',     4),
    # SWIMWEAR
    ('SWIMSUIT',       'SWIMWEAR',   'Swimsuit (one-piece)',  'Banyador',               'Bañador',             1),
    ('BIKINI_TOP',     'SWIMWEAR',   'Bikini top',            'Part de dalt de bikini', 'Bikini top',          2),
    ('BIKINI_BOTTOM',  'SWIMWEAR',   'Bikini bottom',         'Part de baix de bikini', 'Braguita bikini',     3),
    ('SWIM_SHORTS',    'SWIMWEAR',   'Swim shorts',           'Banyador curt home',     'Bañador corto',       4),
    ('BABY_SWIMWEAR',  'SWIMWEAR',   'Baby swimwear',         'Banyador nadó',          'Bañador bebé',        5),
    # ACCESSORIES
    ('HAT_CAP',        'ACCESSORIES','Hat / Cap',             'Gorra / Barret',         'Gorra / Sombrero',    1),
    ('SCARF',          'ACCESSORIES','Scarf',                 'Bufanda',                'Bufanda',             2),
    ('BELT',           'ACCESSORIES','Belt',                  'Cinturó',                'Cinturón',            3),
]


# codi_client tenant actual → codi global canònic
MAPPING = {
    # Ja coincideixen
    'T_SHIRT':        'T_SHIRT',
    'SHIRT':          'SHIRT',
    'BLOUSE':         'BLOUSE',
    'POLO':           'POLO',
    'TOP_SLEEVELESS': 'TOP_SLEEVELESS',
    'BODYSUIT':       'BODYSUIT',
    'SWEATER':        'SWEATER',
    'HOODIE':         'HOODIE',
    'CARDIGAN':       'CARDIGAN',
    'VEST_TOP':       'VEST_TOP',
    'BABY_BODYSUIT':  'BABY_BODYSUIT',
    'BABY_TOP':       'BABY_TOP',
    'TROUSERS':       'TROUSERS',
    'JEANS':          'JEANS',
    'SHORTS':         'SHORTS',
    'LEGGINGS':       'LEGGINGS',
    'SKIRT':          'SKIRT',
    'BABY_LEGGINGS':  'BABY_LEGGINGS',
    'DRESS':          'DRESS',
    'SHIRT_DRESS':    'SHIRT_DRESS',
    'JUMPSUIT':       'JUMPSUIT',
    'PLAYSUIT':       'PLAYSUIT',
    'BABY_ROMPER':    'BABY_ROMPER',
    'BABY_DRESS':     'BABY_DRESS',
    'JACKET':         'JACKET',
    'COAT':           'COAT',
    'PARKA':          'PARKA',
    'GILET':          'GILET',
    'BRA':            'BRA',
    'BRIEFS_WOMAN':   'BRIEFS_WOMAN',
    'BOXERS':         'BOXERS',
    'SWIMSUIT':       'SWIMSUIT',
    'BIKINI_TOP':     'BIKINI_TOP',
    'BIKINI_BOTTOM':  'BIKINI_BOTTOM',
    'SWIM_SHORTS':    'SWIM_SHORTS',
    'BABY_SWIMWEAR':  'BABY_SWIMWEAR',
    'HAT_CAP':        'HAT_CAP',
    'SCARF':          'SCARF',
    'BELT':           'BELT',
    # Duplicats antics → global nou
    'CAM-TOP':        'T_SHIRT',
    'CAM-BRU':        'SHIRT',
    'VAQ-DEN':        'JEANS',
    'PAN-TEL':        'TROUSERS',
    'SHO-BER':        'SHORTS',
    'XAN-LEG':        'LEGGINGS',
    'FAL-SIM':        'SKIRT',
    'VES-SIM':        'SHIRT_DRESS',
    'VES-EST':        'DRESS',
    'MON-JUM':        'JUMPSUIT',
    'JER-PUN':        'SWEATER',
    'CAR-DIG':        'CARDIGAN',
    'CHA-TEI':        'GILET',
    'SUD-SWE':        'HOODIE',
    'TOP-EST':        'TOP_SLEEVELESS',
    'AME-SUI':        'JACKET',
    'ANO-PAR':        'PARKA',
    'ABR-COA':        'COAT',
    'XAQ-BLA':        'JACKET',
    'BAN-BIK':        'SWIMSUIT',
    # Casos especials conservats amb nou codi
    'PEC-PEL':        'LEATHER_GARMENT',
    'GAB-TRE':        'TRENCH_COAT',
    'PIJ-2PC':        'PYJAMA_SET',
}


CODIS_A_ESBORRAR = [
    'CAM-TOP', 'CAM-BRU', 'VAQ-DEN', 'PAN-TEL', 'SHO-BER',
    'XAN-LEG', 'FAL-SIM', 'VES-SIM', 'VES-EST', 'MON-JUM',
    'JER-PUN', 'CAR-DIG', 'CHA-TEI', 'SUD-SWE', 'TOP-EST',
    'AME-SUI', 'ANO-PAR', 'ABR-COA', 'XAQ-BLA', 'BAN-BIK',
]


class Command(BaseCommand):
    help = 'Migra GarmentType a arquitectura Global (public) + Tenant (Opció B, S13-A)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant', default='fhort',
            help='Schema del tenant on aplicar la reassignació (default: fhort)'
        )

    def handle(self, *args, **opts):
        tenant_schema = opts['tenant']

        assert len(GARMENT_TYPE_GLOBALS) == 42, \
            f"Expected 42 globals, got {len(GARMENT_TYPE_GLOBALS)}"
        codis_global = {g[0] for g in GARMENT_TYPE_GLOBALS}
        for cli, glob in MAPPING.items():
            if glob not in codis_global:
                raise ValueError(f"MAPPING {cli!r} apunta a global inexistent: {glob!r}")

        # ── Pas A: crear globals al public ──────────────────────────────────
        self.stdout.write(self.style.WARNING(
            'Pas A: creant 42 GarmentTypeGlobal al schema public...'
        ))
        with schema_context('public'):
            from fhort.pom.models import GarmentTypeGlobal
            with transaction.atomic():
                deleted, _ = GarmentTypeGlobal.objects.all().delete()
                self.stdout.write(f'  {deleted} globals antics esborrats.')
                for codi, grup, nom_en, nom_ca, nom_es, order in GARMENT_TYPE_GLOBALS:
                    GarmentTypeGlobal.objects.create(
                        codi=codi,
                        grup=grup,
                        nom_en=nom_en,
                        nom_ca=nom_ca,
                        nom_es=nom_es,
                        display_order=order,
                        is_system=True,
                        actiu=True,
                    )
            self.stdout.write(f'  {GarmentTypeGlobal.objects.count()} globals creats.')

        # Capturem el mapping global (codi → dades) per usar al tenant
        with schema_context('public'):
            from fhort.pom.models import GarmentTypeGlobal
            global_data = {
                g.codi: {
                    'id': g.id,
                    'nom_en': g.nom_en,
                    'nom_ca': g.nom_ca,
                    'nom_es': g.nom_es,
                    'grup': g.grup,
                }
                for g in GarmentTypeGlobal.objects.all()
            }

        # ── Pas B: reassignar tenant records ────────────────────────────────
        self.stdout.write(self.style.WARNING(
            f'\nPas B: reassignant GarmentType al tenant {tenant_schema}...'
        ))
        with schema_context(tenant_schema):
            from fhort.pom.models import GarmentType, GarmentTypeGlobal as GTG_tenant

            # GarmentTypeGlobal al tenant és una taula local — cal sincronitzar
            # amb les dades del public perquè la FK funcioni dins del schema.
            with transaction.atomic():
                GTG_tenant.objects.all().delete()
                for codi, grup, nom_en, nom_ca, nom_es, order in GARMENT_TYPE_GLOBALS:
                    GTG_tenant.objects.create(
                        codi=codi, grup=grup,
                        nom_en=nom_en, nom_ca=nom_ca, nom_es=nom_es,
                        display_order=order, is_system=True, actiu=True,
                    )
                tenant_global_map = {g.codi: g for g in GTG_tenant.objects.all()}

                reassignats = 0
                no_mapping = []
                for gt in GarmentType.objects.all():
                    codi = gt.codi_client
                    if codi not in MAPPING:
                        no_mapping.append(codi)
                        continue
                    global_codi = MAPPING[codi]
                    g_obj = tenant_global_map[global_codi]
                    gt.garment_type_global = g_obj
                    if not gt.nom_en:
                        gt.nom_en = g_obj.nom_en
                    if not gt.nom_ca:
                        gt.nom_ca = g_obj.nom_ca
                    if not gt.nom_es:
                        gt.nom_es = g_obj.nom_es
                    gt.is_system = True
                    gt.save(update_fields=[
                        'garment_type_global', 'nom_en', 'nom_ca',
                        'nom_es', 'is_system',
                    ])
                    reassignats += 1

            self.stdout.write(f'  {reassignats} GarmentType reassignats.')
            if no_mapping:
                self.stdout.write(self.style.ERROR(
                    f'  SENSE MAPPING ({len(no_mapping)}): {no_mapping}'
                ))

        # ── Pas C: esborrar duplicats ───────────────────────────────────────
        self.stdout.write(self.style.WARNING(
            f'\nPas C: esborrant duplicats antics al tenant {tenant_schema}...'
        ))
        with schema_context(tenant_schema):
            from fhort.pom.models import GarmentType
            qs = GarmentType.objects.filter(codi_client__in=CODIS_A_ESBORRAR)
            n_match = qs.count()
            esborrats, details = qs.delete()
            self.stdout.write(
                f'  {esborrats} registres esborrats (match={n_match}). Detall: {details}'
            )

        # ── Resum ───────────────────────────────────────────────────────────
        with schema_context('public'):
            from fhort.pom.models import GarmentTypeGlobal
            total_public = GarmentTypeGlobal.objects.count()

        with schema_context(tenant_schema):
            from fhort.pom.models import GarmentType
            total_tenant = GarmentType.objects.count()
            nulls = GarmentType.objects.filter(garment_type_global__isnull=True).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ GarmentTypeGlobal (public):       {total_public}'
            f'\n✓ GarmentType ({tenant_schema}):              {total_tenant}'
            f'\n✓ Sense global_id (hauria ser 0):   {nulls}'
        ))
