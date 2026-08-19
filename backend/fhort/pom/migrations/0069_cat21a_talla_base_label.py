# CAT2.1 · PAS (a) (2026-08-07) — la talla base de la regla, per ETIQUETA.
#
# Decisió d'Agus: les regles referencien l'ETIQUETA (`XS`, `S`, `38`), no una FILA d'un run
# concret, i el motor la resol contra el run DEL MODEL. Mateix patró que el creuament de POMs
# (per codi, mai per id) i que el germà `talla_break_label` de la mateixa taula.
#
# Aquest pas és NOMÉS-OMPLE i additiu: la FK es queda. El pas (b) —retirar-la— només es fa si
# aquí el casament és del 100%, i el `RunPython` d'aquí sota AVORTA si no ho és, en comptes de
# deixar el forat per a més endavant. Conviure és estat vàlid; mentir, no.
from django.db import migrations, models


def backfill(apps, schema_editor):
    GradingRule = apps.get_model('pom', 'GradingRule')

    total = GradingRule.objects.count()
    if not total:
        return
    # `update` massiu des de la FK: una sola query per schema, i idempotent (només toca les
    # que encara no porten etiqueta).
    pendents = GradingRule.objects.filter(talla_base_label='')
    for regla in pendents.select_related('talla_base').iterator(chunk_size=500):
        etiqueta = (regla.talla_base.etiqueta or '').strip() if regla.talla_base_id else ''
        if etiqueta:
            GradingRule.objects.filter(pk=regla.pk).update(talla_base_label=etiqueta)

    # ── L'AUDITORIA, dins la mateixa transacció ───────────────────────────────────────
    sense = GradingRule.objects.filter(talla_base_label='').count()
    if sense:
        exemples = list(GradingRule.objects.filter(talla_base_label='')
                        .values_list('pk', 'talla_base_id')[:10])
        raise RuntimeError(
            f'CAT2.1(a) ATURA · {sense} de {total} regles s\'han quedat sense etiqueta de talla '
            f'base. El pas (b) NO es pot fer i conviure és estat vàlid. Exemples '
            f'(regla, talla_base_id): {exemples}'
        )


def enrere(apps, schema_editor):
    """Buida a posta: el camp cau sencer amb l'AddField d'aquesta mateixa migració."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0068_c6_pas1_garmenttype_grup_ref'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradingrule',
            name='talla_base_label',
            field=models.CharField(blank=True, default='', help_text="L'etiqueta, resolta contra el run del model. Buit = encara no backfillat.", max_length=30, verbose_name='Talla base (etiqueta)'),
        ),
        migrations.RunPython(backfill, enrere),
    ]
