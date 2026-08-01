"""C1-ins — les unicitats de `models_app` incorporen la INSTÀNCIA, i les comportes la tanquen.

Fa en una sola migració el que la capa va fer en dues (`0071_capa_unicitats` +
`0072_capa_comporta_c1`), perquè és una sola decisió: obrir la clau i tancar-la alhora.

**T3 · LES CLAUS.** Mateix argument de seguretat que a la capa: la clau nova són les mateixes
columnes **més una**, o sigui estrictament més permissiva, i avui `instancia` és constant
('') a totes les files → 0 duplicats latents possibles. La vella es retira a la MATEIXA
migració (`AlterUniqueTogether` ho fa en un sol pas; `POMPlacement`, que fa servir un
`UniqueConstraint` amb nom, ho fa amb RemoveConstraint + AddConstraint).

El nom del constraint de `POMPlacement` torna a créixer amb els camps
(`..._view_capa` → `..._view_capa_instancia`) pel mateix motiu que a C1: un constraint que
en digui quatre i en guardi cinc menteix a qui llegeixi l'esquema. Verificat que cap
consumidor el referencia pel nom.

**T4 · LES COMPORTES `*_instancia_gate_cins`.** Cinc, una per taula de `0073`. Mateixa
bastida que les de capa i pel mateix motiu, amb l'eix canviat: la cadena de lectors encara
indexa per `pom_id` (o per `(pom_id, capa)`), i una segona instància escrita per accident
abans de FASE_2/FASE_3 no petaria enlloc — es fondria dins les llistes com la primera.
**C4-ins les retira per migració**, al costat de les seves germanes de capa.

APLICACIÓ SEGURA: el 100% de les files tenen `instancia = ''` (default de columna de
`0073`), auditat per SQL contra `information_schema` als 3 schemas abans d'aplicar → la
validació que Postgres fa en crear cada CHECK no pot fallar.

**LA QUE NO ÉS BASTIDA: `..._instancia_exigeix_nom` (decisió D1).** `~Q(instancia__gt='',
nom_fitxa='')` — una mesura amb instància i sense nom de fitxa és il·legal per construcció, i
això sobreviu a C4-ins. Si una mesura es desdobla, l'única cosa que fa que les dues files
siguin distingibles per a un humà —al croquis, a la taula, al paper— és el `nom_fitxa`. Dues
files «pit» sense res que les separi visualment no són dues mesures: són un duplicat amb
aparença de dada bona. Amb la comporta tancada la condició és trivialment certa a totes les
files: no rebutja res que avui passi.

⚠️ `ModelGradingRule` no hi és, ni aquí ni a `0073`: no travessa cap dels dos eixos
(decisió Montse, «gradúen igual»). El test `test_instancia_comporta_cins` ho vigila.
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_tenantconfig_legal_footer'),
        ('fitting', '0019_capa_comporta_c1'),
        ('models_app', '0073_instancia_mesures'),
        ('pom', '0055_capa_comporta_c1'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='pomplacement',
            name='uniq_pomplacement_item_pom_view_capa',
        ),
        migrations.AlterUniqueTogether(
            name='basemeasurement',
            unique_together={('model', 'pom', 'capa', 'instancia')},
        ),
        migrations.AlterUniqueTogether(
            name='modelgradingoverride',
            unique_together={('model', 'pom', 'size_label', 'capa', 'instancia')},
        ),
        migrations.AlterUniqueTogether(
            name='sizecheckline',
            unique_together={('size_check', 'pom', 'capa', 'instancia')},
        ),
        migrations.AddConstraint(
            model_name='basemeasurement',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='models_app_basemeasurement_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='basemeasurement',
            constraint=models.CheckConstraint(condition=models.Q(('instancia__gt', ''), ('nom_fitxa', ''), _negated=True), name='models_app_basemeasurement_instancia_exigeix_nom'),
        ),
        migrations.AddConstraint(
            model_name='measurementchangelog',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='models_app_measurementchangelog_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='modelgradingoverride',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='models_app_modelgradingoverride_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='pomplacement',
            constraint=models.UniqueConstraint(fields=('item_fitxer', 'pom', 'view_slot', 'capa', 'instancia'), name='uniq_pomplacement_item_pom_view_capa_instancia'),
        ),
        migrations.AddConstraint(
            model_name='pomplacement',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='models_app_pomplacement_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='sizecheckline',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='models_app_sizecheckline_instancia_gate_cins'),
        ),
    ]
