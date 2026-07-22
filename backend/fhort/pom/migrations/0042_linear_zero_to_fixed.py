"""A2 — LINEAR + increment 0 + SENSE break  →  FIXED (conversió de dades).

LLEI (Agus, 2026-07-22). Una regla `LINEAR` amb delta 0 i sense trencament no gradua
res: `_apply_rule` retorna `base_val` per a totes les talles, exactament igual que
`FIXED`. La conversió és **matemàticament neutra** — no mou cap valor graduat ni 0,01;
l'únic que canvia és l'etiqueta `grading_type_applied` d'un recàlcul futur (LINEAR →
FIXED), que passa a dir la veritat: aquesta mesura no canvia entre talles.

L'autoria de regles noves així ja està bloquejada al backend (`set_pom_regim_view`,
codi `LINEAR_INCREMENT_ZERO`) i la presentació ja les dibuixa com a FIXED
(`frontend/src/utils/gradingRegime.js`). Aquesta migració tanca el forat de les
preexistents.

REQUISITS DURS complerts:
  · **Mai silenciosa** — imprimeix quantes i quines (id + ruleset/model pare + POM).
  · **El break és sagrat** — cap regla amb `talla_break_label` informat o
    `increment_break` no-zero es toca, encara que el delta base sigui 0.
  · **Reversible** — `backwards` és un NOOP DOCUMENTAT: no es desfà. Reetiquetar de
    tornada a LINEAR tornaria a fabricar la mentida que aquesta migració elimina, i
    com que la conversió no altera cap valor, no hi ha res a restaurar. Baixar de
    migració no deixa la BD inconsistent.
  · Inclou les 9 regles del rule set 115 (S10 Brownie) — autoritzat explícitament.

Rulesets/models afectats a staging al moment d'escriure-la: rs 115/175-188/210 i
models 163/174/267/268/269/292/293/523.
"""

from django.db import migrations
from django.db.models import Q
from django_tenants.utils import get_public_schema_name


def _zero_delta_no_break(qs):
    """Regles amb delta base efectiu 0 i CAP trencament informat.

    Delta base efectiu = `increment_base` si està poblat (forma canònica), si no
    `increment` (fallback legacy que llegeix `_apply_rule`).
    """
    delta_zero = (
        Q(increment_base=0)
        | (Q(increment_base__isnull=True) & (Q(increment=0) | Q(increment__isnull=True)))
    )
    sense_break = (
        (Q(talla_break_label__isnull=True) | Q(talla_break_label=''))
        & (Q(increment_break__isnull=True) | Q(increment_break=0))
    )
    return qs.filter(Q(logica='LINEAR') & delta_zero & sense_break)


def _log(titol, files):
    print(f'  [A2] {titol}: {len(files)} regla/es')
    for linia in files:
        print(f'       {linia}')


def forwards(apps, schema_editor):
    schema = schema_editor.connection.schema_name
    GradingRule = apps.get_model('pom', 'GradingRule')
    ModelGradingRule = apps.get_model('models_app', 'ModelGradingRule')

    print(f'\n[A2 · LINEAR+0 → FIXED] esquema "{schema}"')

    cataleg = _zero_delta_no_break(GradingRule.objects.all()).select_related('rule_set', 'pom')
    files = [
        f'GradingRule#{r.id} · rule_set={r.rule_set_id} ({r.rule_set.nom}) '
        f'· pom={r.pom_id} ({r.pom.codi_client}) · actiu={r.actiu} '
        f'· increment_base={r.increment_base} increment={r.increment}'
        for r in cataleg
    ]
    ids_cataleg = [r.id for r in cataleg]
    _log('pom.GradingRule', files)

    # `pom` és app SHARED → aquesta migració corre TAMBÉ a 'public', on models_app (app
    # només-tenant) no té taules. La regla resident només existeix dins d'un tenant.
    if schema == get_public_schema_name():
        ids_resident = []
        print('  [A2] models_app.ModelGradingRule: omès (esquema public, app només-tenant)')
    else:
        # ModelGradingRule.pom és un FK sense constraint de BD (cross-schema) → no select_related.
        resident = _zero_delta_no_break(ModelGradingRule.objects.all())
        files_r = [
            f'ModelGradingRule#{r.id} · model={r.model_id} · pom={r.pom_id} '
            f'· origen={r.origen} actiu={r.actiu} '
            f'· increment_base={r.increment_base} increment={r.increment}'
            for r in resident
        ]
        ids_resident = [r.id for r in resident]
        _log('models_app.ModelGradingRule', files_r)

    if ids_cataleg:
        GradingRule.objects.filter(id__in=ids_cataleg).update(logica='FIXED')
    if ids_resident:
        ModelGradingRule.objects.filter(id__in=ids_resident).update(logica='FIXED')

    print(f'  [A2] convertides: {len(ids_cataleg)} de catàleg + {len(ids_resident)} residents '
          f'= {len(ids_cataleg) + len(ids_resident)} (esquema "{schema}")\n')


def backwards(apps, schema_editor):
    """NOOP DOCUMENTAT — vegeu la capçalera del mòdul.

    No es reetiqueta de tornada a LINEAR: seria restaurar la mentida, i com que la
    conversió no ha alterat cap valor numèric no hi ha cap dada a recuperar.
    """
    print('[A2] backwards: NOOP deliberat (cap valor alterat; reetiquetar enrere '
          'restauraria LINEAR+0, que és precisament el que s\'ha eliminat).')


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0041_remove_garmenttype_targets_recomanats'),
        ('models_app', '0058_alter_modelgradingrule_origen'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
