"""Sembra el self-customer del tenant (Customer is_self=True) amb codi = Client.codi_tenant.

Es guarda per-schema via migrate_schemas, però SALTA el schema `public` (no és un tenant
operatiu). Per a `fhort` → Customer(codi='FHT', is_self=True). El self-customer és el fallback
del codi-gen (helper customer_code_for): garanteix que cap model quedi sense prefix.

⚠️ PENDENT (futur): enganxar aquesta mateixa lògica a l'onboarding de tenants nous, perquè el
self-customer es creï automàticament en provisionar un tenant (no només per aquesta migració).
"""
from django.db import migrations, connection


def seed_self_customer(apps, schema_editor):
    if connection.schema_name == 'public':
        return

    # Codi i nom del tenant actual. Prioritza connection.tenant (el fixa migrate_schemas);
    # si no, cau a una consulta del model de tenant per schema_name.
    tenant = getattr(connection, 'tenant', None)
    codi = (getattr(tenant, 'codi_tenant', '') or '').strip().upper() if tenant else ''
    nom = getattr(tenant, 'nom', '') if tenant else ''
    if not codi:
        try:
            from django_tenants.utils import get_tenant_model
            t = get_tenant_model().objects.get(schema_name=connection.schema_name)
            codi = (t.codi_tenant or '').strip().upper()
            nom = t.nom
        except Exception:
            return
    if not codi:
        return

    Customer = apps.get_model('tasks', 'Customer')
    if Customer.objects.filter(is_self=True).exists():
        return
    # Si ja hi ha un Customer amb aquest codi (no-self), el promovem a self en lloc de duplicar.
    existing = Customer.objects.filter(codi=codi).first()
    if existing:
        if not existing.is_self:
            existing.is_self = True
            existing.save(update_fields=['is_self'])
        return
    Customer.objects.create(codi=codi, nom=nom or codi, is_self=True)


def unseed_self_customer(apps, schema_editor):
    if connection.schema_name == 'public':
        return
    Customer = apps.get_model('tasks', 'Customer')
    Customer.objects.filter(is_self=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0019_customer'),
    ]

    operations = [
        migrations.RunPython(seed_self_customer, unseed_self_customer),
    ]
