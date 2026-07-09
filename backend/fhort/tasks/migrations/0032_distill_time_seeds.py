# Destil·la les cel·les TaskTimeEstimate NOMÉS teòriques (n=0, valor de perfil L/M/P) a
# llavors de tenant per-task (TimeSeed scope='task', origen='MIGRACIO') i neteja el valor
# teòric de la cel·la, perquè el Welford només contingui mostres REALS. Les cel·les amb
# n>0 (dada real observada, madura o no) queden INTACTES.
from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations
from django.db.models import Avg


def distill_seeds(apps, schema_editor):
    TaskTimeEstimate = apps.get_model('tasks', 'TaskTimeEstimate')
    TimeSeed = apps.get_model('tasks', 'TimeSeed')

    # Una llavor per task amb cel·les teòriques: mitjana dels seus estimated_minutes
    # (col·lapsa els perfils L/M/P ponderats per la població d'items).
    rows = (TaskTimeEstimate.objects.filter(n=0, estimated_minutes__isnull=False)
            .values('task_type__code')
            .annotate(avg=Avg('estimated_minutes')))
    for r in rows:
        minuts = int(Decimal(str(r['avg'])).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        if minuts <= 0:
            continue
        TimeSeed.objects.update_or_create(
            scope='task', key=r['task_type__code'],
            defaults=dict(minuts=minuts, origen='MIGRACIO'),
        )

    # Neteja: el valor teòric surt de la cel·la (n=0 → estimated_minutes=None). n>0 intacte.
    TaskTimeEstimate.objects.filter(n=0).update(estimated_minutes=None)


def restore_seeds(apps, schema_editor):
    # Reversa best-effort: recol·loca a cada cel·la teòrica nul·la el minuts de la llavor
    # MIGRACIO del seu task (pla, sense el matís de perfil), i elimina les llavors MIGRACIO.
    TaskTimeEstimate = apps.get_model('tasks', 'TaskTimeEstimate')
    TaskType = apps.get_model('tasks', 'TaskType')
    TimeSeed = apps.get_model('tasks', 'TimeSeed')
    for s in TimeSeed.objects.filter(scope='task', origen='MIGRACIO'):
        tt = TaskType.objects.filter(code=s.key).first()
        if tt:
            (TaskTimeEstimate.objects
             .filter(task_type_id=tt.id, n=0, estimated_minutes__isnull=True)
             .update(estimated_minutes=s.minuts))
    TimeSeed.objects.filter(scope='task', origen='MIGRACIO').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0031_timeseed_created_at_timeseed_origen_and_more'),
    ]

    operations = [
        migrations.RunPython(distill_seeds, restore_seeds),
    ]
