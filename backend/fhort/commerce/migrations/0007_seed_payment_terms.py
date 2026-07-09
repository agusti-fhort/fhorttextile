from django.db import migrations

# Condicions de pagament per defecte (B3a). Idempotent: get_or_create per code.
# 50-50: 50% a l'inici (dia 0) + 50% a l'entrega. El segon és "a l'entrega", que NO té data
# coneguda a l'oferta → days_offset=0 i és el text del PDF qui ho explica.
# TODO B3b/B4: quan existeixi DeliveryNote, el 2n venciment es recalcularà de la data d'entrega real.
TERMS = [
    ('50-50', "50% inici / 50% entrega", [(50, 0, 0), (50, 0, 1)]),
    ('30D', "30 dies data document", [(100, 30, 0)]),
    ('60D', "60 dies data document", [(100, 60, 0)]),
]


def seed(apps, schema_editor):
    PaymentTerms = apps.get_model('commerce', 'PaymentTerms')
    PaymentTermLine = apps.get_model('commerce', 'PaymentTermLine')
    for code, name, lines in TERMS:
        terms, _ = PaymentTerms.objects.get_or_create(code=code, defaults={'name': name})
        for pct, days, pos in lines:
            PaymentTermLine.objects.get_or_create(
                terms=terms, position=pos,
                defaults={'percentage': pct, 'days_offset': days})


def unseed(apps, schema_editor):
    PaymentTerms = apps.get_model('commerce', 'PaymentTerms')
    PaymentTerms.objects.filter(code__in=[c for c, _, _ in TERMS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('commerce', '0006_paymentterms_paymenttermline'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
