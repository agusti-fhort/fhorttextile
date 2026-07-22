# P7 (2026-07-22) — D-CONS "un rol, un vincle": jubilació del FK legacy
# GradingRuleSet.target en favor de la M2M `targets` (font única del ventall).
#
# Ordre: RunPython(reconciliació FK→M2M) → RemoveField(target).
# Patró calcat de 0021_remove_sizesystem_target_sizesystem_targets (que va fer el mateix
# per a SizeSystem); la diferència és que aquí la M2M JA existeix des de 0009, que mai va
# portar data-migration — d'aquí les 10 divergències FK↔M2M documentades a la diagnosi
# (§B2.6). Aquesta migració les resol abans d'esborrar el camp.
#
# pom és TENANT_APP: migrate_schemas la corre a cada esquema, reconciliant els lligams
# propis de cadascun.

from django.db import migrations, models


def reconcilia_fk_a_m2m(apps, schema_editor):
    """Cap lligam del FK legacy es perd: tot `target` no NULL ha de constar a `targets`.

    Cas real que això cobreix (schema fhort, 2026-07-22): rs 98 té FK plena i M2M BUIDA →
    sense aquest pas, esborrar el camp perdria l'únic target del ruleset. Els altres 9
    divergents ja tenen el FK contingut a la M2M (que a més hi afegeix els targets que el
    FK singular no podia expressar) → són no-ops idempotents.
    """
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')
    afegits = 0
    for rs in GradingRuleSet.objects.filter(target__isnull=False):
        if not rs.targets.filter(pk=rs.target_id).exists():
            rs.targets.add(rs.target_id)
            afegits += 1
            print(f"  · rs {rs.pk} {rs.nom!r}: target {rs.target_id} recuperat cap a la M2M")
    print(f"[P7] reconciliació FK→M2M: {afegits} lligam(s) recuperat(s) "
          f"({schema_editor.connection.schema_name})")


def restaura_m2m_a_fk(apps, schema_editor):
    """Reverse: el primer target de la M2M torna a la FK (RemoveField.reverse l'ha recreat).

    Reversibilitat parcial i honesta: els rulesets amb més d'un target NO són representables
    per una FK singular (8 casos reals) — se'n conserva el primer i es deixa traça.
    """
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')
    for rs in GradingRuleSet.objects.all():
        tgts = list(rs.targets.all()[:2])
        if not tgts:
            continue
        rs.target = tgts[0]
        rs.save(update_fields=['target'])
        if len(tgts) > 1:
            print(f"  ⚠ rs {rs.pk} {rs.nom!r}: >1 target; el FK només en reté el primer")


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0042_linear_zero_to_fixed'),
    ]

    operations = [
        migrations.RunPython(reconcilia_fk_a_m2m, restaura_m2m_a_fk),
        migrations.RemoveField(
            model_name='gradingruleset',
            name='target',
        ),
    ]
