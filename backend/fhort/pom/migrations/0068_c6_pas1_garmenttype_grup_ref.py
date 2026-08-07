# C6 · PAS 1 (2026-08-07) — `GarmentType.grup`: la FK neix, el string es queda.
#
# Decisió 1 de DIAGNOSI_VOCABULARIS §2.6 («l'amo del vocabulari és la BD»), en dos passos com
# manava el brief: aquí s'afegeix la FK i es fa el backfill PER CODI; el pas 2 —retirar el
# string— no es fa avui.
#
# 🛑 PER QUÈ EL PAS 2 S'ATURA, i no és prudència genèrica: al tenant `los` hi ha un
# `GarmentType` (`BUTTONED_TOPS`, grup `'TOPS'`) i la taula `GarmentGroup` és **BUIDA**. Allà
# el backfill no té amb què resoldre el codi, i retirar el string hi perdria l'única informació
# de grup que existeix. A `fhort` el backfill és net (21 files, 8 codis, tots existents) i a
# `public` no hi ha cap `GarmentType`. V. REPORT_CATALEG_TALLES.md §C6.
#
# El backfill és idempotent i NOMÉS-OMPLE: no toca cap fila que ja porti FK.
import django.db.models.deletion
from django.db import migrations, models


def backfill(apps, schema_editor):
    GarmentType = apps.get_model('pom', 'GarmentType')
    GarmentGroup = apps.get_model('pom', 'GarmentGroup')

    per_codi = {g.codi: g.pk for g in GarmentGroup.objects.all()}
    if not per_codi:
        return                             # `los`: no hi ha vocabulari a què lligar-se
    for gt in GarmentType.objects.filter(grup_ref__isnull=True).exclude(grup=''):
        pk = per_codi.get((gt.grup or '').strip())
        if pk:
            GarmentType.objects.filter(pk=gt.pk).update(grup_ref_id=pk)


def enrere(apps, schema_editor):
    """Buida a posta: el camp cau sencer amb l'AddField d'aquesta mateixa migració."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0067_c4_unicitat_ordre_talla'),
    ]

    operations = [
        migrations.AddField(
            model_name='garmenttype',
            name='grup_ref',
            field=models.ForeignKey(blank=True, help_text='Pas 1 de C6: conviu amb `grup`. NULL = el codi no existeix a GarmentGroup.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='garment_types', to='pom.garmentgroup', verbose_name='Grup (FK)'),
        ),
        migrations.RunPython(backfill, enrere),
    ]
