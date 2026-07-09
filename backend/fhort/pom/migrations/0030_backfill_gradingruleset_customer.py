"""N2-3 — Backfill GradingRuleSet.customer des de SizeSystem.customer_codi → Customer.

Data migration (DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08). Es guarda del schema `public`: la
FK apunta a tasks.Customer (tenant-only), que NO existeix a public. Reporta els rulesets que no
resolen (customer_codi present però Customer inexistent); NO inventa cap client.
"""
from django.db import migrations


def backfill_customer(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return  # Customer és tenant-only; a public no hi ha dades reals de ruleset.
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')
    Customer = apps.get_model('tasks', 'Customer')
    resolved = no_codi = unresolved = 0
    misses = []
    for rs in GradingRuleSet.objects.select_related('size_system').all():
        codi = (rs.size_system.customer_codi or '').strip() if rs.size_system_id else ''
        if not codi:
            no_codi += 1
            continue
        cust = Customer.objects.filter(codi=codi).first()
        if cust is None:
            unresolved += 1
            misses.append((rs.id, codi))
            continue
        if rs.customer_id != cust.id:
            rs.customer_id = cust.id
            rs.save(update_fields=['customer'])
        resolved += 1
    print(f"[N2-3 backfill customer @ {conn.schema_name}] resolts={resolved} "
          f"sense_customer_codi={no_codi} NO_RESOLTS={unresolved} {misses}")


def reverse(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')
    GradingRuleSet.objects.update(customer=None)


class Migration(migrations.Migration):
    dependencies = [
        ('pom', '0029_gradingruleset_customer_customerpomalias'),
    ]
    operations = [
        migrations.RunPython(backfill_customer, reverse),
    ]
