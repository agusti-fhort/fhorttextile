# CAT2 (2026-08-07) — l'última banda de BABY_MONTHS: 24-30 → 24-36.
#
# C2 (`0065`) va deixar la talla `24M` amb `age_months_max=30`, aplicant el pas local (+6) per
# a l'única fila que no té «següent» de qui heretar el límit. Era el valor auditable, i el
# report el va marcar per validar. La revisió independent ha portat la prova que faltava, i no
# és una opinió sinó **dues sèries de la mateixa casa**:
#
#   · `BABY_EU_CM` · la banda que segueix `18-24` és **`24-36`** (talla 68)
#   · `TODDLER_EU` · la seva primera banda és **`24-36`** (talla 92), i encaixa exactament
#     amb el final de BABY_MONTHS: on acaba l'un comença l'altre
#
# O sigui que 30 obria un forat de 6 mesos entre `BABY_MONTHS` i `TODDLER_EU` que a les dades
# de la casa no hi és. Idempotent i quirúrgic: només aquella fila i només si encara diu 30.
from django.db import migrations

CODI = 'BABY_MONTHS'
ETIQUETA = '24M'


def alinea(apps, schema_editor):
    SizeDefinition = apps.get_model('pom', 'SizeDefinition')

    SizeDefinition.objects.filter(
        size_system__codi=CODI, etiqueta=ETIQUETA,
        age_months_min=24, age_months_max=30,
    ).update(age_months_max=36)


def enrere(apps, schema_editor):
    """Buida a posta: tornar a 30 seria reobrir el forat entre BABY_MONTHS i TODDLER_EU."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0070_cat23_sizingprofile_unicitat'),
    ]

    operations = [
        migrations.RunPython(alinea, enrere),
    ]
