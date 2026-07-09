# Seed canònic del catàleg de tasques (DISSENY_CATALEG_TASQUES §1.6).
# Idempotent: update_or_create PER CODE (mai per PK) → no remapeja les FK existents
# (ModelTask PROTECT, TaskTimeEstimate CASCADE conserven el seu task_type_id).
# Reversible = noop (no esborrem cap TaskType viu en revertir).
from django.db import migrations

# (default_order, code, name, fase, tipus, eina, mode, facturable)
CATALEG = [
    (5,  'design_review',  'Revisió de disseny',       'Disseny',     'Externa-lliure', None,      None,           True),
    (6,  'design_clarify', 'Aclariments amb disseny',  'Disseny',     'Externa-lliure', None,      None,           False),
    (10, 'pattern_digit',  'Patró digitalització',     'Dev. tècnic', 'Interna',        'patro',   'digitalitzar', True),
    (20, 'pattern_cad',    'Patró CAD',                'Dev. tècnic', 'Interna',        'patro',   'disseny_base', True),
    (30, 'pattern_hand',   'Patró a mà',               'Dev. tècnic', 'Externa-lliure', None,      None,           True),
    (40, 'pom',            'Definició POM',            'Dev. tècnic', 'Interna',        'mesures', 'autoria_base', True),
    (45, 'size_check',     'Mesurar prenda',           'Dev. tècnic', 'Interna',        'mesures', 'presa',        True),
    (46, 'grading',        'Escalat',                  'Dev. tècnic', 'Interna',        'escalat', 'propagacio',   True),
    (50, 'tech_sheet',     'Fitxa tècnica',            'Dev. tècnic', 'Interna',        'fitxa',   'document',     True),
    (55, 'pattern_review', 'Revisió de patró CAD',     'Dev. tècnic', 'Interna',        'patro',   'revisio',      True),
    (70, 'bom',            'Definició BOM',            'Dev. tècnic', 'Interna',        'fitxa',   'bom',          True),
    (81, 'scaling',        'Escalat CAD',              'Dev. tècnic', 'Interna',        'patro',   'escalat',      True),
    (82, 'marking',        'Marcada',                  'Dev. tècnic', 'Interna',        'patro',   'marcada',      True),
    (90, 'audit',          'Auditoria de model',       'Dev. tècnic', 'Externa-lliure', None,      None,           False),
]


def seed(apps, schema_editor):
    TaskType = apps.get_model('tasks', 'TaskType')
    for default_order, code, name, fase, tipus, eina, mode, facturable in CATALEG:
        TaskType.objects.update_or_create(
            code=code,
            defaults=dict(
                name=name, default_order=default_order, active=True,
                fase=fase, tipus=tipus, eina=eina, mode=mode, facturable=facturable,
            ),
        )


def unseed(apps, schema_editor):
    # Noop: revertir l'esquema (0024) no ha de destruir dades del catàleg.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0024_tasktype_eina_tasktype_facturable_tasktype_fase_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
