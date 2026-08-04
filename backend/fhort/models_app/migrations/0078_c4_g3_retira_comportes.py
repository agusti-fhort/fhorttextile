"""C4 · G3 — L'AJUST MANUAL I EL CROQUIS. 20 comportes → 12.

Grup 3 de 4. Dues taules que no són la mesura ni la presa, sinó el que un humà en fa:
· `ModelGradingOverride` — pinar una cel·la de talla a mà. Pinar la M de la sisa dreta no pot
  moure l'esquerra; `escalat/ajustar-talla` ja hi escriu per la identitat sencera (`959147a5`).
· `PomPlacement` — lligar la mesura al CROQUIS. És on «dues cares, dues línies» es veurà de
  debò: la sisa dreta i l'esquerra són dues cotes al dibuix, no una.

🚩 La decisió de producte sobre la COL·LOCACIÓ AUTOMÀTICA (una cota o dues per a un POM amb
germanes, i com s'anomenen) segueix OBERTA — v. `b56b2dfb`. Retirar la comporta no la pren:
la deixa possible. Fins que es prengui, cap camí lliga una cota a una germana triada a
l'atzar, que és el que sí que estava tancat.

⚠️ Les dues invariants no es toquen. ⚠️ Parany del rollback: v. la migració de G1.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0077_c4_g2_retira_comportes'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='modelgradingoverride',
            name='models_app_modelgradingoverride_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='modelgradingoverride',
            name='models_app_modelgradingoverride_instancia_gate_cins',
        ),
        migrations.RemoveConstraint(
            model_name='pomplacement',
            name='models_app_pomplacement_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='pomplacement',
            name='models_app_pomplacement_instancia_gate_cins',
        ),
    ]
