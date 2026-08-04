"""C1/T3 — les unicitats de `models_app` incorporen la CAPA.

Mateix argument de seguretat que a `pom/0054_capa_unicitats`: la clau nova són les mateixes
columnes **més una**, o sigui estrictament més permissiva, i avui `capa` és constant
('exterior') a totes les files → 0 duplicats latents possibles.

`POMPlacement` no fa servir `unique_together` sinó un `UniqueConstraint` amb nom: DROP del
vell + ADD del nou, i el NOM canvia amb els camps (`..._view` → `..._view_capa`) perquè un
constraint que en digui tres i en guardi quatre menteix a qui llegeixi l'esquema. Verificat
que cap consumidor el referencia pel nom.

També canvia l'`ordering` de `BaseMeasurement` a ['model','capa','ordre','pom']: quan hi
hagi més d'una capa, la fitxa les vol AGRUPADES i no barrejades per `ordre`. Avui és un
no-op OBSERVABLE —amb una sola capa el valor és constant i l'ordre relatiu de les files no
es mou—, i el fumeig de base-stages ho verifica byte a byte a T5. (`base_stages_view` ni
tan sols hi cau: ordena explícitament per `ordre, pom__codi_client`.) `AlterModelOptions`
no toca la BD: només l'ORM.

⚠️ `ModelGradingRule` no hi és, ni aquí ni a T2: la regla es comparteix entre capes
(decisió de domini, argumentada al seu docstring).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0070_capa_mesures'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='basemeasurement',
            options={
                'ordering': ['model', 'capa', 'ordre', 'pom'],
                'verbose_name': 'Mesura base',
                'verbose_name_plural': 'Mesures base',
            },
        ),
        migrations.AlterUniqueTogether(
            name='basemeasurement',
            unique_together={('model', 'pom', 'capa')},
        ),
        migrations.AlterUniqueTogether(
            name='modelgradingoverride',
            unique_together={('model', 'pom', 'size_label', 'capa')},
        ),
        migrations.AlterUniqueTogether(
            name='sizecheckline',
            unique_together={('size_check', 'pom', 'capa')},
        ),
        migrations.RemoveConstraint(
            model_name='pomplacement',
            name='uniq_pomplacement_item_pom_view',
        ),
        migrations.AddConstraint(
            model_name='pomplacement',
            constraint=models.UniqueConstraint(
                fields=('item_fitxer', 'pom', 'view_slot', 'capa'),
                name='uniq_pomplacement_item_pom_view_capa'),
        ),
    ]
