# Normalitza el code 'Audit' → 'audit' (convenció slug-minúscula de la resta del catàleg).
# Renombra NOMÉS el camp code de la fila existent (mateix PK → FK ModelTask/TaskTimeEstimate
# intactes) i actualitza les allow-lists de dades (UserProfile.permisos['tasks']) que hi
# apuntin, perquè el rename no orfeni cap permís de tècnic.
from django.db import migrations


def _remap_permisos(UserProfile, old, new):
    for p in UserProfile.objects.all():
        perms = p.permisos or {}
        tasks = perms.get('tasks')
        if isinstance(tasks, list) and old in tasks:
            perms['tasks'] = [new if c == old else c for c in tasks]
            p.permisos = perms
            p.save(update_fields=['permisos'])


def normalize(apps, schema_editor):
    TaskType = apps.get_model('tasks', 'TaskType')
    TaskType.objects.filter(code='Audit').update(code='audit')
    _remap_permisos(apps.get_model('accounts', 'UserProfile'), 'Audit', 'audit')


def denormalize(apps, schema_editor):
    TaskType = apps.get_model('tasks', 'TaskType')
    TaskType.objects.filter(code='audit').update(code='Audit')
    _remap_permisos(apps.get_model('accounts', 'UserProfile'), 'audit', 'Audit')


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0029_delete_tipologiamodel'),
        ('accounts', '0003_userprofile_jornada_override'),
    ]

    operations = [
        migrations.RunPython(normalize, denormalize),
    ]
