"""B1 (2026-07-25) — repuntat de les mesures base V1 cap al seu BaseSet.

V1 penjava el valor de l'item pelat i llegia la talla base de GarmentTypeItem.base_size_definition.
Aquesta migració materialitza el món que aquelles files ja tenien implícit: per cada item amb
mesures base, crea l'ItemBaseSet (item × system de la seva talla base × fit REGULAR) i hi repunta
les files.

El size_system NO s'assumeix: es llegeix de gti.base_size_definition.size_system_id (a `fhort`,
shirt_woven → ALPHA_EU_M, talla base L). Un item amb mesures però SENSE base_size_definition no
té món declarat i les seves files queden òrfenes a posta — 0049 (el NOT NULL) fallarà i això és
el senyal, no un silenci.

Idempotent: get_or_create pel set, i només toca files amb base_set NULL.
"""
from django.db import migrations


def forward(apps, schema_editor):
    ItemBaseMeasurement = apps.get_model('pom', 'ItemBaseMeasurement')
    ItemBaseSet = apps.get_model('pom', 'ItemBaseSet')
    GarmentTypeItem = apps.get_model('tasks', 'GarmentTypeItem')
    FitType = apps.get_model('pom', 'FitType')

    # 'pom' és SHARED: aquesta migració corre TAMBÉ a `public`, on 'tasks' (tenant-only) no té
    # taules. Sense aquest guard, l'ORDERING del Meta d'ItemBaseMeasurement (que fa JOIN cap a
    # tasks_garmenttypeitem) peta amb ProgrammingError abans i tot de mirar si hi ha files.
    if 'tasks_garmenttypeitem' not in schema_editor.connection.introspection.table_names():
        return

    # .order_by() buida l'ordering del Meta: aquí només volem els ids, no el JOIN que arrossega.
    orphans = ItemBaseMeasurement.objects.filter(base_set__isnull=True).order_by()
    item_ids = sorted(set(orphans.values_list('garment_type_item_id', flat=True)))
    if not item_ids:
        return

    # Convenció de lookup del BaseSet (vegeu pom.models.normalize_fit_type): «cap fit» → REGULAR.
    # Si el schema no té FitType sembrat (avui `los`), el set neix amb fit_type NULL i el
    # resolver hi cau igual, perquè normalitza amb el mateix criteri.
    regular = FitType.objects.filter(codi='REGULAR').first()

    for item_id in item_ids:
        gti = GarmentTypeItem.objects.filter(pk=item_id).first()
        if gti is None or gti.base_size_definition_id is None:
            # Món no declarat: no inventem ni el sistema ni la talla base. Files òrfenes → 0049 avisa.
            continue
        base_size = gti.base_size_definition
        base_set, _ = ItemBaseSet.objects.get_or_create(
            garment_type_item_id=item_id,
            size_system_id=base_size.size_system_id,
            fit_type=regular,
            defaults={
                'base_size_definition_id': base_size.pk,
                # Coherent amb l'origen de les files que hi repuntem (les 37 de `fhort` són MANUAL):
                # el set no neix d'una promoció ni d'un paquet, sinó del que un tècnic va escriure.
                'origen': 'MANUAL',
            },
        )
        ItemBaseMeasurement.objects.filter(
            garment_type_item_id=item_id, base_set__isnull=True,
        ).update(base_set_id=base_set.pk)


def backward(apps, schema_editor):
    # Desfem el repuntat i els sets que aquesta migració hauria pogut crear. No esborrem sets
    # amb mesures encara penjades (no n'hi hauria d'haver després del clear, però no forcem).
    ItemBaseMeasurement = apps.get_model('pom', 'ItemBaseMeasurement')
    ItemBaseSet = apps.get_model('pom', 'ItemBaseSet')
    ItemBaseMeasurement.objects.update(base_set=None)
    ItemBaseSet.objects.filter(measurements__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0047_itembaseset'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
